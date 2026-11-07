import csv
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).parent / "fixtures"
OFFICIAL = ROOT / "validation"            # put the official Validation Set here at kickoff
SYNTH = ROOT / "validation_synthetic"
VALIDATION = OFFICIAL if OFFICIAL.is_dir() and any(OFFICIAL.glob("*.xml")) else SYNTH

os.environ["NETCHECK_OFFLINE"] = "1"

from netcheck import guardrail, history  # noqa: E402
from netcheck.analyzer import analyze_bytes, analyze_folder, write_csvs  # noqa: E402
from netcheck.models import mask_mac  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_HOME", str(tmp_path / "home"))


def _rows(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def test_validation_set_matches_answer_key(tmp_path):
    fp, sp = write_csvs(analyze_folder(VALIDATION), tmp_path)
    got = _rows(fp)
    exp = _rows(ROOT / "expected_validation_findings.csv")
    assert got[0] == exp[0]
    assert sorted(got[1:]) == sorted(exp[1:]), "findings differ from answer key"
    assert len(got) - 1 == 24
    assert _rows(sp) == _rows(ROOT / "expected_validation_scores.csv")


def test_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write_csvs(analyze_folder(VALIDATION), a)
    write_csvs(analyze_folder(VALIDATION), b)
    for name in ("findings.csv", "scores.csv"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_broken_file_does_not_crash():
    r = analyze_bytes(b"<nmaprun><host><address addr=", "x.xml")
    assert not r.ok and r.score_str == "ERROR" and r.error


@pytest.mark.parametrize("payload", [
    b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><nmaprun>&x;</nmaprun>',
    b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><nmaprun>&b;</nmaprun>',
    b"",
    b"not xml at all",
    b"<html><body>hi</body></html>",
])
def test_hostile_input_rejected(payload):
    r = analyze_bytes(payload, "evil.xml")
    assert not r.ok


def test_masked_mac():
    assert mask_mac("aa:bb:cc:dd:ee:ff") == "AA:BB:CC:XX:XX:XX"
    r = analyze_folder(VALIDATION)
    for res in r:
        for d in res.devices:
            assert d.mac_masked == "" or d.mac_masked.endswith("XX:XX:XX")


@pytest.mark.parametrize("target", ["8.8.8.8", "1.1.1.0/24", "100.64.1.1", "10.0.0.0/8", "192.168.50.0/24",
                                    "127.0.0.1", "224.0.0.1", "not-an-ip"])
def test_guardrail_refuses(target):
    allow = guardrail.build_allowlist("172.20.10.0/28")
    with pytest.raises(guardrail.ScopeError):
        guardrail.check_target(target, allow, confirmed=True)


def test_guardrail_requires_confirm():
    allow = guardrail.build_allowlist("172.20.10.0/28")
    with pytest.raises(guardrail.ScopeError, match="--confirm"):
        guardrail.check_target("172.20.10.0/28", allow, confirmed=False)
    assert guardrail.check_target("172.20.10.5", allow, confirmed=True) == "172.20.10.5/32"


def test_guardrail_rejects_public_allowlist_entry():
    with pytest.raises(guardrail.ScopeError):
        guardrail.build_allowlist("172.20.10.0/28", ["8.8.8.0/24"])


def test_history_before_after_shows_3_resolved():
    res = {r.file: r for r in analyze_folder(VALIDATION)}
    a = history.save(res["V6a_before.xml"], "v6")
    b = history.save(res["V6b_after.xml"], "v6")
    assert history.previous_of(b) == a
    d = history.diff(history.load(a), history.load(b))
    assert len(d["resolved_findings"]) == 3
    assert d["old_score"] == 60 and d["new_score"] == 100
    history.delete_all()
    assert history.list_scans() == []


def test_change_alerts():
    res = {r.file: r for r in analyze_folder(VALIDATION)}
    d = history.diff(res["V6b_after.xml"], res["V6a_before.xml"])
    al = history.alerts(d, "en")
    assert any("23/tcp" in x for x in al)


def test_ui_escapes_banners_and_shows_results():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    evil = (b'<?xml version="1.0"?><nmaprun><host><address addr="192.168.1.5" addrtype="ipv4"/>'
            b'<hostnames><hostname name="&lt;script&gt;alert(1)&lt;/script&gt;"/></hostnames><ports>'
            b'<port protocol="tcp" portid="80"><state state="open"/><service name="http"/>'
            b'<script id="http-title" output="&lt;img src=x onerror=alert(1)&gt; Login"/></port></ports></host></nmaprun>')
    c = TestClient(app)
    r = c.post("/upload", files={"files": ("evil.xml", evil, "text/xml")}, follow_redirects=True)
    assert r.status_code == 200
    assert "<script>alert(1)" not in r.text and "&lt;script&gt;" in r.text
    assert "<img src=x" not in r.text
    assert "90" in r.text
    r = c.post("/ask", data={"question": "what do I fix first?", "scan_id": history.latest_id()})
    assert r.status_code == 200 and "192.168.1.5" in r.text


def test_offline_assistant_grounded():
    from netcheck.assistant import Session, offline_answer
    s = Session(lang="en")
    s.load_file(str(VALIDATION / "V3_small_office.xml"))
    assert "3389" in offline_answer(s, "which device is the most dangerous?")
    assert "does not show" in offline_answer(s, "what is port 8443?")
    assert "not in our official risk list" in offline_answer(s, "what is port 631?")
