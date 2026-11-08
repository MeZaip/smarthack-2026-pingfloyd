"""Technical report for an IT person (nmap style .txt): from a file, from the history, over the API and the CLI."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

from netcheck import history
from netcheck.core.analysis import analyze_file
from netcheck.explain.technical import technical_report

ROOT = Path(__file__).resolve().parent.parent
SYN = ROOT / "tests" / "fixtures" / "synthetic"
LAB = ROOT / "tests" / "fixtures" / "lab"
FULL_MAC = re.compile(r"\b(?:[0-9A-F]{2}:){5}[0-9A-F]{2}\b", re.I)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "history.sqlite"))
    monkeypatch.setenv("NETCHECK_EXPORTS", str(tmp_path / "exports"))
    monkeypatch.setenv("NETCHECK_LLM_PROVIDER", "none")
    from netcheck.web import app as web
    web._cache.clear()
    yield
    web._cache.clear()


def _body(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.startswith(("Raport generat", "Report generated")))


@pytest.mark.parametrize("name", sorted(p.name for p in SYN.glob("*.xml") if p.name != "V7_broken.xml"))
def test_report_has_every_host_port_and_finding(name):
    a = analyze_file(SYN / name)
    text = technical_report(a, "en")
    assert f"{a.score}/100" in text
    assert f") = {a.score}" in text                                   # the score calculation is shown
    for h in a.scan.up_hosts:
        assert f"({h.ip})" in text or f"for {h.ip}" in text
        for p in h.open_ports:
            assert re.search(rf"^{p.portid}/{p.protocol}\s+open\s", text, re.M), (h.ip, p.portid)
    for f in a.findings:
        assert f.code in text and f.ip in text
    assert not FULL_MAC.search(text.replace("XX:XX:XX:XX:", ""))     # only masked MACs
    assert all(line == line.rstrip() for line in text.splitlines())


def test_versions_and_titles_are_in_the_report():
    text = technical_report(analyze_file(SYN / "V4_legacy.xml"), "ro")
    assert "vsftpd 2.3.4" in text and "BusyBox telnetd" in text and "Router Setup" in text
    assert "max(0, 100 - (20 + 20 + 10 + 10 + 10 + 5)) = 25" in text
    assert "[TELNET_OPEN]" in text and "CIS Control 4.8" in text


def test_unreadable_file_gives_a_short_error_report():
    text = technical_report(analyze_file(SYN / "V7_broken.xml"), "en")
    assert "ERROR" in text and "HOSTS" not in text


def test_report_from_the_history_equals_the_report_from_the_file():
    a = analyze_file(SYN / "V4_legacy.xml")
    with history.open_history() as conn:
        sid, _ = history.save(conn, a)
        loaded = history.load_analysis(conn, sid)
    assert _body(technical_report(loaded, "ro")) == _body(technical_report(a, "ro"))


def test_old_history_databases_get_the_new_columns(tmp_path):
    import sqlite3
    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(db)
    con.executescript("""CREATE TABLE scans (scan_id INTEGER PRIMARY KEY AUTOINCREMENT, file TEXT NOT NULL, scanned_at INTEGER,
        saved_at INTEGER NOT NULL, network_score INTEGER NOT NULL);
        CREATE TABLE ports (scan_id INTEGER NOT NULL, ip TEXT NOT NULL, protocol TEXT NOT NULL, port INTEGER NOT NULL, service TEXT NOT NULL);
        INSERT INTO scans (file, scanned_at, saved_at, network_score) VALUES ('old.xml', 1, 1, 90);
        INSERT INTO ports VALUES (1, '10.0.0.1', 'tcp', 80, 'http');""")
    con.commit(); con.close()
    conn = history.connect(db)
    a = history.load_analysis(conn, 1)
    assert a.scan.hosts == [] and a.scan.args == ""
    sid, _ = history.save(conn, analyze_file(SYN / "V1_home_basic.xml"))
    assert history.load_analysis(conn, sid).scan.args
    conn.close()


def test_report_lists_changes_since_the_previous_check():
    with history.open_history() as conn:
        b, _ = history.save(conn, analyze_file(SYN / "V6a_before.xml"))
        a, _ = history.save(conn, analyze_file(SYN / "V6b_after.xml"))
        text = technical_report(history.load_analysis(conn, a), "en", history.changes(conn, b, a))
    assert "CHANGES SINCE THE PREVIOUS CHECK" in text and "V6a_before.xml (60/100) -> 100/100 (+40)" in text


def test_api_report_downloads_and_saves_a_txt(tmp_path):
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    c = TestClient(app)
    c.get("/")
    up = c.post("/api/v1/upload", files=[("files", (p.name, p.read_bytes(), "text/xml"))
                                         for p in (LAB / "lab_01_before.xml", LAB / "lab_03_final.xml")])
    ids = up.json()["saved"]
    assert c.get(f"/api/v1/report/{ids[-1]}").status_code in (404, 405)    # writes a file: POST only
    r = c.post(f"/api/v1/report/{ids[-1]}?lang=en")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    assert 'filename="safehouse_report_lab_03_final_' in r.headers["content-disposition"]
    assert "Nmap scan report for" in r.text and "CHANGES SINCE THE PREVIOUS CHECK" in r.text
    saved = list((tmp_path / "exports").glob("safehouse_report_*.txt"))
    assert len(saved) == 1 and saved[0].read_text(encoding="utf-8") == r.text
    assert c.post("/api/v1/report/9999").status_code == 404


def test_cli_technical_report(tmp_path):
    out = tmp_path / "r.txt"
    p = subprocess.run([sys.executable, "-m", "netcheck", "report", str(SYN / "V2_smart_home.xml"), "--technical",
                        "--lang", "en", "--out", str(out)], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "Nmap scan report for" in out.read_text(encoding="utf-8")
