"""Live scan from the web UI: same guardrail as the CLI, consent, CSRF, local-only, background job."""
import shutil
import time
from pathlib import Path

import pytest

from netcheck import history
from netcheck.net import netdetect, scanner

SYN = Path(__file__).parent / "fixtures" / "synthetic"
NET = netdetect.NetworkInfo(interface="wlan0", ip="172.20.10.2", netmask="255.255.255.240",
                            subnet="172.20.10.0/28", gateway="172.20.10.1")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "history.sqlite"))
    monkeypatch.setenv("NETCHECK_SCANS_DIR", str(tmp_path / "scans"))
    monkeypatch.setenv("NETCHECK_LLM_PROVIDER", "none")
    monkeypatch.delenv("NETCHECK_ALLOWLIST", raising=False)
    from netcheck.web import app as web, livescan
    monkeypatch.setattr(livescan.netdetect, "detect", lambda: NET)
    monkeypatch.setattr(web, "_is_local", lambda request: True)
    livescan.reset()
    web._cache.clear()
    yield
    livescan.reset()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    return TestClient(app)


def _csrf():
    from netcheck.web import app as web
    return web._CSRF


def _fake_nmap(calls):
    def run_scan(target, out_dir, interactive=True):
        calls.append((target, interactive))
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        dst = out / "scan_live.xml"
        shutil.copy(next(p for p in sorted(SYN.glob("*.xml")) if "broken" not in p.name), dst)
        return dst
    return run_scan


def _wait(livescan):
    for _ in range(200):
        if livescan.current().state != "running":
            return livescan.current()
        time.sleep(0.02)
    raise AssertionError("scan job never finished")


def test_scan_page_shows_detected_network(client):
    r = client.get("/scan?lang=en")
    assert r.status_code == 200
    assert "172.20.10.0/28" in r.text and 'name="csrf"' in r.text


@pytest.mark.parametrize("target", ["8.8.8.8", "192.168.0.0/24", "10.0.0.0/8", "not-an-ip"])
def test_out_of_scope_targets_are_refused_and_nmap_never_runs(client, monkeypatch, target):
    calls = []
    monkeypatch.setattr(scanner, "run_scan", _fake_nmap(calls))
    r = client.post("/scan?lang=en", data={"target": target, "confirm": "yes", "csrf": _csrf()})
    assert r.status_code == 400
    assert "REFUSED" in r.text or "not a valid" in r.text
    assert calls == []


def test_scan_needs_confirmation(client, monkeypatch):
    calls = []
    monkeypatch.setattr(scanner, "run_scan", _fake_nmap(calls))
    r = client.post("/scan?lang=en", data={"target": "", "csrf": _csrf()})
    assert r.status_code == 400 and "explicit consent" in r.text
    assert calls == []


def test_scan_without_csrf_token_is_refused(client, monkeypatch):
    calls = []
    monkeypatch.setattr(scanner, "run_scan", _fake_nmap(calls))
    r = client.post("/scan", data={"target": "", "confirm": "yes", "csrf": "forged"})
    assert r.status_code == 403 and calls == []


def test_scan_from_another_computer_is_refused(client, monkeypatch):
    from netcheck.web import app as web
    monkeypatch.setattr(web, "_is_local", lambda request: False)
    calls = []
    monkeypatch.setattr(scanner, "run_scan", _fake_nmap(calls))
    r = client.post("/scan", data={"target": "", "confirm": "yes", "csrf": _csrf()})
    assert r.status_code == 403 and calls == []


def test_confirmed_scan_runs_in_background_and_lands_in_history(client, monkeypatch):
    from netcheck.web import livescan
    calls = []
    monkeypatch.setattr(scanner, "run_scan", _fake_nmap(calls))
    r = client.post("/scan?lang=en", data={"target": "172.20.10.5", "confirm": "yes", "csrf": _csrf()},
                    follow_redirects=False)
    assert r.status_code == 303
    job = _wait(livescan)
    assert job.state == "done", job.message
    assert calls == [("172.20.10.5/32", False)]          # guardrail-normalised, never prompts for sudo
    with history.open_history() as conn:
        assert history.scan_ids(conn) == [job.scan_id]
    page = client.get("/scan?lang=en").text
    assert "Scan finished" in page and f"id={job.scan_id}" in page


def test_missing_sudo_rights_show_a_clear_message(client, monkeypatch):
    from netcheck.web import livescan

    def no_root(target, out_dir, interactive=True):
        raise scanner.NeedsRootError("sudo: a password is required")
    monkeypatch.setattr(scanner, "run_scan", no_root)
    client.post("/scan?lang=en", data={"confirm": "yes", "csrf": _csrf()})
    assert _wait(livescan).state == "needs_root"
    assert "admin rights" in client.get("/scan?lang=en").text
