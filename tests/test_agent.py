"""Local agent (web/agent.py + /api/v1) and the one-click flow: security, live scan job with a fake
nmap, "I fixed it - check", conversation, delete, app lifecycle, OS elevation, launcher helpers."""
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest

from netcheck import history
from netcheck.core.analysis import analyze_file
from netcheck.net import elevate, netdetect, scanner
from netcheck.net.netdetect import NetworkInfo

SYN = Path(__file__).parent / "fixtures" / "synthetic"
NET = NetworkInfo(interface="wlan0", ip="192.168.1.20", netmask="255.255.255.0", subnet="192.168.1.0/24",
                  gateway="192.168.1.1")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "history.sqlite"))
    monkeypatch.setenv("NETCHECK_SCANS", str(tmp_path / "scans"))
    monkeypatch.setenv("NETCHECK_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("NETCHECK_LLM_PROVIDER", "none")
    monkeypatch.delenv("NETCHECK_ALLOW_ANY_HOST", raising=False)
    monkeypatch.setattr(netdetect, "detect", lambda: NET)
    from netcheck.web import agent, api_v1
    from netcheck.web import app as web
    monkeypatch.setattr(agent, "wifi_name", lambda: "RSH-07")
    monkeypatch.setattr(scanner, "find_nmap", lambda: "nmap")
    web._cache.clear()
    api_v1.jobs = agent.ScanJobs(on_saved=web._remember)
    api_v1._test_runner = None
    yield
    api_v1._test_runner = None
    web._cache.clear()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    c = TestClient(app)
    c.get("/api/scans")          # any page served by the agent sets the session cookie
    return c


def fake_nmap(fixture="V2_smart_home.xml", seen=None, returncode=0):
    def run(cmd):
        if seen is not None:
            seen.append(cmd)
        shutil.copy(SYN / fixture, cmd[cmd.index("-oX") + 1])
        return subprocess.CompletedProcess(cmd, returncode, "", "")
    return run


def wait_job(client, job_id, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        j = client.get(f"/api/v1/scan/{job_id}").json()
        if j["status"] != "running":
            return j
        time.sleep(0.05)
    raise AssertionError("job did not finish")


# ------------------------------------------------------------------ security of the local agent
def test_other_hosts_are_refused(client):
    assert client.get("/", headers={"host": "evil.example"}).status_code == 403          # DNS rebinding
    assert client.get("/api/v1/status", headers={"host": "127.0.0.1.evil.example"}).status_code == 403


def test_state_changes_need_the_session_cookie():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    fresh = TestClient(app)                                     # never loaded a page -> no cookie
    r = fresh.post("/api/v1/scan", json={"confirm": True})
    assert r.status_code == 403 and r.json()["error"]["code"] == "session"
    assert fresh.delete("/api/v1/history").status_code == 403
    assert fresh.post("/history/delete").status_code == 403       # old HTML forms are protected too


def test_cross_site_request_is_refused(client):
    r = client.post("/api/v1/heartbeat", headers={"origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden_origin"
    assert client.post("/api/v1/heartbeat", headers={"origin": "http://127.0.0.1:8000"}).status_code == 200


def test_session_cookie_is_strict_and_httponly(client):
    cookie = client.get("/").headers["set-cookie"].lower()
    assert "samesite=strict" in cookie and "httponly" in cookie


# ------------------------------------------------------------------ status
def test_status_for_the_consent_screen(client):
    st = client.get("/api/v1/status").json()
    assert st["network"] == {"ok": True, "subnet": "192.168.1.0/24", "ip": "192.168.1.20",
                             "gateway": "192.168.1.1", "wifi": "RSH-07"}
    assert st["nmap"] is True and st["has_history"] is False and st["scan"] is None
    assert st["ai"] == {"online": False}


def test_status_explains_missing_network(client, monkeypatch):
    def boom():
        raise netdetect.NetworkDetectError("x")
    monkeypatch.setattr(netdetect, "detect", boom)
    net = client.get("/api/v1/status?lang=en").json()["network"]
    assert net["ok"] is False and net["code"] == "no_network" and "Wi-Fi" in net["message"]


# ------------------------------------------------------------------ live scan job
def test_scan_needs_consent(client):
    r = client.post("/api/v1/scan?lang=en", json={"confirm": False})
    assert r.status_code == 400 and r.json()["error"]["code"] == "need_consent"


def test_scan_job_end_to_end(client):
    from netcheck.web import api_v1
    seen = []
    api_v1.jobs._run_nmap = fake_nmap(seen=seen)
    r = client.post("/api/v1/scan", json={"confirm": True})
    assert r.status_code == 202
    job = wait_job(client, r.json()["id"])
    assert job["status"] == "done" and job["score"] == 40 and job["scan_id"] is not None
    cmd = seen[0]
    assert cmd[-1] == "192.168.1.0/24"                      # always the network we are on
    assert "--log-errors" in cmd and "-oN" in cmd            # nmap's own errors are kept for diagnosis
    assert "--exclude" not in cmd                            # every device is scanned, this computer too
    assert cmd[cmd.index("--max-rate") + 1] == "100"         # rules of engagement
    assert [s["network_score"] for s in client.get("/api/scans").json()] == [40]
    page = client.get(f"/?id={job['scan_id']}").text
    assert "data-verify" in page and 'id="chat-form"' in page


def test_scan_target_is_never_taken_from_the_page(client):
    from netcheck.web import api_v1
    seen = []
    api_v1.jobs._run_nmap = fake_nmap(seen=seen)
    r = client.post("/api/v1/scan", json={"confirm": True, "target": "8.8.8.8"})
    wait_job(client, r.json()["id"])
    assert seen[0][-1] == "192.168.1.0/24"


def test_public_network_is_refused(client, monkeypatch):
    monkeypatch.setattr(netdetect, "detect", lambda: NetworkInfo("eth0", "8.8.8.8", "255.255.255.0", "8.8.8.0/24", ""))
    r = client.post("/api/v1/scan", json={"confirm": True})
    assert r.status_code == 400 and r.json()["error"]["code"] == "refused"
    assert client.get("/api/v1/status").json()["network"]["code"] == "refused"


def test_missing_nmap_is_explained(client, monkeypatch):
    monkeypatch.setattr(scanner, "find_nmap", lambda: None)
    r = client.post("/api/v1/scan?lang=ro", json={"confirm": True})
    assert r.status_code == 503 and "nmap.org" in r.json()["error"]["message"]


def test_permission_refused_in_dialog(client):
    from netcheck.web import api_v1

    def denied(cmd):
        raise elevate.ElevationDenied("no")
    api_v1.jobs._run_nmap = denied
    job = wait_job(client, client.post("/api/v1/scan?lang=ro", json={"confirm": True}).json()["id"])
    assert job["status"] == "error" and job["error"]["code"] == "denied" and "„Da”" in job["error"]["message"]


def test_failed_nmap_is_an_error_not_a_crash(client, capsys):
    from netcheck.web import api_v1
    api_v1.jobs._run_nmap = fake_nmap(fixture="V7_broken.xml")
    job = wait_job(client, client.post("/api/v1/scan", json={"confirm": True}).json()["id"])
    assert job["error"]["code"] == "scan_failed" and "XML unusable" in job["error"]["detail"]
    assert client.get("/api/scans").json() == []
    assert "failed: scan_failed" in capsys.readouterr().err          # the reason reaches the terminal / app.log


def test_nmap_errors_are_explained(client):
    from netcheck.web import api_v1

    def no_npcap(cmd):
        Path(cmd[cmd.index("-oN") + 1]).write_text("# Nmap 7.95\nWARNING: Npcap is not installed\n")
        return subprocess.CompletedProcess(cmd, 1, "", "")
    api_v1.jobs._run_nmap = no_npcap
    job = wait_job(client, client.post("/api/v1/scan", json={"confirm": True}).json()["id"])
    d = job["error"]["detail"]
    assert "no XML written" in d and "Npcap is not installed" in d and "exit code 1" in d


def test_odd_exit_code_with_a_good_xml_is_accepted(client):
    from netcheck.web import api_v1
    api_v1.jobs._run_nmap = fake_nmap(returncode=1)
    job = wait_job(client, client.post("/api/v1/scan", json={"confirm": True}).json()["id"])
    assert job["status"] == "done" and job["score"] == 40


def test_only_one_scan_at_a_time(client):
    from netcheck.web import api_v1
    gate = threading.Event()

    def slow(cmd):
        gate.wait(5)
        return fake_nmap()(cmd)
    api_v1.jobs._run_nmap = slow
    first = client.post("/api/v1/scan", json={"confirm": True}).json()
    second = client.post("/api/v1/scan", json={"confirm": True})
    assert second.status_code == 409 and second.json()["error"]["code"] == "busy"
    assert client.get("/api/v1/status").json()["scan"]["id"] == first["id"]   # a reloaded page can follow it
    gate.set()
    assert wait_job(client, first["id"])["status"] == "done"


# ------------------------------------------------------------------ "I fixed it - check"
def _saved(name="V2_smart_home.xml"):
    with history.open_history() as conn:
        return history.save(conn, analyze_file(SYN / name))[0]


def _nmap_reply(state):
    return (f'<nmaprun><host><status state="up"/><address addr="192.168.1.40" addrtype="ipv4"/><ports>'
            f'<port protocol="tcp" portid="554"><state state="{state}"/><service name="rtsp"/></port>'
            f'</ports></host></nmaprun>').encode()


@pytest.mark.parametrize("state,status", [("closed", "resolved"), ("open", "still_open")])
def test_verify_one_fix(client, state, status):
    from netcheck.web import api_v1
    sid = _saved()
    api_v1._test_runner = lambda cmd: _nmap_reply(state)
    r = client.post("/api/v1/verify?lang=ro", json={"scan_id": sid, "ip": "192.168.1.40", "port": 554,
                                                     "code": "CAMERA_STREAM_EXPOSED"})
    assert r.status_code == 200 and r.json()["status"] == status


def test_verify_udp_asks_for_a_full_check(client):
    sid = _saved()
    r = client.post("/api/v1/verify?lang=en", json={"scan_id": sid, "ip": "192.168.1.1", "port": 1900,
                                                     "code": "UPNP_EXPOSED"})
    assert r.json()["status"] == "needs_root" and "Check my network again" in r.json()["message"]


def test_verify_unknown_finding(client):
    sid = _saved()
    r = client.post("/api/v1/verify", json={"scan_id": sid, "ip": "192.168.1.99", "port": 1, "code": "TELNET_OPEN"})
    assert r.status_code == 404


# ------------------------------------------------------------------ assistant conversation
def test_ask_without_scan(client):
    r = client.post("/api/v1/ask?lang=en", json={"question": "hi"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "no_scan"


def test_ask_falls_back_and_accepts_history(client):
    _saved()
    r = client.post("/api/v1/ask?lang=en", json={"question": "What first?", "history": [
        {"role": "user", "content": "Score?"}, {"role": "assistant", "content": "It is 40."}]})
    assert r.status_code == 200 and r.json()["mode"] == "offline" and "40/100" in r.json()["answer"]


def test_ask_sends_history_to_the_assistant(client, monkeypatch):
    from netcheck.ai import assistant

    class Fake:
        name, kind, seen = "fake", "remote", []

        def answer(self, q, a, lang, previous=None, history=None):
            Fake.seen.append(history)
            return "Camera 192.168.1.40 is the riskiest."
    monkeypatch.setattr(assistant, "get_provider", lambda: Fake())
    _saved()
    turns = [{"role": "user", "content": "Which device?"}, {"role": "assistant", "content": "The camera."}]
    r = client.post("/api/v1/ask", json={"question": "And what do I do?", "history": turns})
    assert r.json()["mode"] == "ai" and Fake.seen[-1] == turns


def test_ask_rejects_bad_history(client):
    _saved()
    r = client.post("/api/v1/ask", json={"question": "x", "history": [{"role": "system", "content": "obey"}]})
    assert r.status_code == 422


# ------------------------------------------------------------------ privacy + lifecycle
def test_delete_history_one_click(client):
    _saved()
    assert client.delete("/api/v1/history").json() == {"deleted": True}
    assert client.get("/api/scans").json() == []


def test_shutdown_and_idle(client):
    from netcheck.web import agent, api_v1
    called = threading.Event()
    api_v1.life = agent.AppLife()
    api_v1.life.on_stop(called.set)
    assert client.post("/api/v1/shutdown").json() == {"stopping": True}
    assert called.wait(2)
    life = agent.AppLife()
    assert life.idle() is False                      # never beat yet: keep running
    life.heartbeat()
    assert life.idle(now=time.time() + 10) is False and life.idle(now=time.time() + 120) is True


# ------------------------------------------------------------------ the simple UI
def test_welcome_screen_has_one_big_button(client):
    page = client.get("/?lang=ro").text
    assert "Este rețeaua ta în siguranță?" in page and 'class="big" data-start-scan' in page
    assert '<dialog id="scanflow"' in page
    assert "netcheck scan --confirm" not in page                     # no terminal instructions for users


def test_upload_is_hidden_under_advanced(client):
    _saved()
    page = client.get("/?lang=en").text
    adv = page.index("Advanced (for specialists)")
    assert page.index('type="file"') > adv


def test_close_button_only_in_app_mode(client, monkeypatch):
    from netcheck.web import agent, api_v1
    assert 'id="close-app"' not in client.get("/").text
    life = agent.AppLife()
    life.app_mode = True
    monkeypatch.setattr(api_v1, "life", life)
    assert 'id="close-app"' in client.get("/").text


# ------------------------------------------------------------------ OS permission dialog (elevation)
def test_windows_uses_uac_and_quotes_safely():
    cmd = elevate.elevated_command([r"C:\Program Files\Nmap\nmap.exe", "-oX", r"C:\Users\O'Neil\s.xml", "10.0.0.0/28"],
                                   system="Windows", admin=False)
    script = cmd[-1]
    assert cmd[0] == "powershell" and "-Verb RunAs" in script and "-Wait" in script
    assert r"'C:\Program Files\Nmap\nmap.exe'" in script and "O''Neil" in script    # PowerShell-escaped
    assert "NativeErrorCode" in script                                               # language-independent


def test_admin_runs_directly():
    assert elevate.elevated_command(["nmap", "x"], system="Windows", admin=True) == ["nmap", "x"]


def test_linux_without_desktop_uses_non_interactive_sudo(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert elevate.elevated_command(["nmap"], system="Linux", admin=False)[:2] == ["sudo", "-n"]


@pytest.mark.parametrize("system,code,stderr,exc", [
    ("Windows", elevate.WINDOWS_CANCELLED, "", elevate.ElevationDenied),
    ("Linux", 1, "sudo: a password is required", elevate.ElevationUnavailable),
    ("Darwin", 1, "execution error: User canceled. (-128)", elevate.ElevationDenied),
])
def test_refusal_is_recognised(system, code, stderr, exc, monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    fake = lambda cmd, **kw: subprocess.CompletedProcess(cmd, code, "", stderr)  # noqa: E731
    with pytest.raises(exc):
        elevate.run_elevated(["nmap"], run=fake, system=system, admin=False)


def test_elevated_success_returns_process():
    fake = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "ok", "")  # noqa: E731
    assert elevate.run_elevated(["nmap"], run=fake, system="Windows", admin=False).returncode == 0


# ------------------------------------------------------------------ launcher
def test_launcher_helpers(monkeypatch):
    from netcheck import launcher
    assert 1024 < launcher.free_port() < 65536
    monkeypatch.setenv("NETCHECK_AI_URL", "https://ai.netcheck.example")
    assert launcher.maybe_start_gateway() is None               # real users: our server, nothing to start
    monkeypatch.delenv("NETCHECK_AI_URL")
    monkeypatch.delenv("NETCHECK_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("NETCHECK_GATEWAY_BACKEND", "claude")
    assert launcher.maybe_start_gateway() is None               # no key on this machine: built-in texts


def test_pythonw_without_console_does_not_crash(monkeypatch):
    import sys
    from netcheck import launcher
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    launcher._no_console_safe()
    print("still works")
    assert sys.stdout is not None


# ------------------------------------------------------------------ device names on live scans (net/identify.py)
LIVE_XML = b'''<?xml version="1.0"?>
<!DOCTYPE nmaprun>
<nmaprun start="1794070000"><host><status state="up"/><address addr="192.168.1.2" addrtype="ipv4"/>
<address addr="6A:11:22:33:8F:72" addrtype="mac"/><hostnames/><ports>
<port protocol="tcp" portid="445"><state state="open"/><service name="microsoft-ds"/></port></ports>
<hostscript><script id="nbstat" output="NetBIOS name: DESKTOP-AB12, NetBIOS user: &lt;unknown&gt;"/></hostscript></host>
<host><status state="up"/><address addr="192.168.1.1" addrtype="ipv4"/><address addr="EE:11:22:33:A3:64" addrtype="mac"/>
<hostnames/><ports><port protocol="tcp" portid="53"><state state="open"/><service name="domain"/></port></ports></host>
</nmaprun>'''


def test_live_scan_uses_names_the_devices_tell_us(client):
    from netcheck.web import api_v1
    seen = []

    def run(cmd):
        seen.append(cmd)
        Path(cmd[cmd.index("-oX") + 1]).write_bytes(LIVE_XML)
        return subprocess.CompletedProcess(cmd, 0, "", "")
    api_v1.jobs._run_nmap = run
    job = wait_job(client, client.post("/api/v1/scan", json={"confirm": True}).json()["id"])
    scripts = seen[0][seen[0].index("--script") + 1].split(",")
    assert scripts[0] == "http-title" and "nbstat" in scripts and "dns-service-discovery" in scripts
    scan = client.get(f"/api/scans/{job['scan_id']}").json()
    codes = {(f["ip"], f["finding_code"]) for f in scan["findings"]}
    assert ("192.168.1.2", "SMB_EXPOSED") in codes
    assert ("192.168.1.2", "UNKNOWN_DEVICE") not in codes          # it told us its name: DESKTOP-AB12
    assert ("192.168.1.1", "UNKNOWN_DEVICE") in codes              # nameless + private MAC: still unknown
    assert job["score"] == 100 - 10 - 5


def test_file_analysis_is_not_changed_by_name_discovery(tmp_path):
    """The Test Set path (`analyze`) judges files exactly as given."""
    from netcheck.core.analysis import analyze_file as af
    f = tmp_path / "x.xml"
    f.write_bytes(LIVE_XML)
    assert ("192.168.1.2", "UNKNOWN_DEVICE") in {(x.ip, x.code) for x in af(f).findings}


def test_unknown_device_evidence_explains_private_mac(tmp_path):
    from netcheck.core.analysis import analyze_file as af
    f = tmp_path / "x.xml"
    f.write_bytes(LIVE_XML)
    ev = next(x.evidence for x in af(f).findings if x.ip == "192.168.1.1" and x.code == "UNKNOWN_DEVICE")
    assert "private (random)" in ev


def test_hostile_names_are_ignored():
    from netcheck.net import identify
    bad = LIVE_XML.replace(b"DESKTOP-AB12", b"&lt;script&gt;alert(1)&lt;/script&gt;")
    assert "192.168.1.2" not in identify.discovered_names(bad)


def test_this_computer_is_scanned_and_named(client, monkeypatch):
    from netcheck.web import agent, api_v1
    monkeypatch.setattr(agent.socket, "gethostname", lambda: "LAPTOP-ZAIP.local")
    me = LIVE_XML.replace(b"192.168.1.1", b"192.168.1.20").replace(b'<address addr="EE:11:22:33:A3:64" addrtype="mac"/>', b"")

    def run(cmd):
        Path(cmd[cmd.index("-oX") + 1]).write_bytes(me)
        return subprocess.CompletedProcess(cmd, 0, "", "")
    api_v1.jobs._run_nmap = run
    job = wait_job(client, client.post("/api/v1/scan", json={"confirm": True}).json()["id"])
    scan = client.get(f"/api/scans/{job['scan_id']}").json()
    mine = next(d for d in scan["devices"] if d["ip"] == "192.168.1.20")       # NET.ip = this computer
    assert mine["hostname"] == "LAPTOP-ZAIP"
    assert ("192.168.1.20", "UNKNOWN_DEVICE") not in {(f["ip"], f["finding_code"]) for f in scan["findings"]}


# ------------------------------------------------------------------ UI: chat never opens the scan dialog; "this computer"
def test_only_scan_buttons_open_the_scan_dialog(client):
    import re
    sid = _saved()
    page = client.get(f"/?id={sid}").text
    form = re.search(r'<form id="chat-form"[^>]*>', page).group(0)
    assert "data-scan-id" in form and "data-start-scan" not in form
    assert re.search(r"\sdata-scan[\s=>]", page) is None                     # the old, ambiguous attribute is gone
    verify = re.findall(r"<button[^>]*data-verify[^>]*>", page)
    assert verify and all("data-start-scan" not in b for b in verify)
    assert 'document.querySelectorAll("[data-start-scan]")' in page


def test_this_computer_is_highlighted(client, monkeypatch):
    from netcheck.web import app as web
    monkeypatch.setattr(netdetect, "detect", lambda: NetworkInfo("wlan0", "192.168.1.40", "255.255.255.0",
                                                                   "192.168.1.0/24", "192.168.1.1"))
    monkeypatch.setitem(web._me, "at", 0.0)
    sid = _saved()
    page = client.get(f"/?id={sid}&lang=ro").text
    assert "💻 Acesta e calculatorul tău" in page and 'class="room' in page and " me\"" in page
    assert 'class="me-row"' in page


def test_no_network_means_no_highlight_and_no_crash(client, monkeypatch):
    from netcheck.web import app as web

    def boom():
        raise netdetect.NetworkDetectError("x")
    monkeypatch.setattr(netdetect, "detect", boom)
    monkeypatch.setitem(web._me, "at", 0.0)
    sid = _saved()
    r = client.get(f"/?id={sid}")
    assert r.status_code == 200 and 'class="me-row"' not in r.text and "badge-me\">" not in r.text
