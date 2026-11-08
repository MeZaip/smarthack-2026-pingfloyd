"""Local history (SQLite): before/after from saved scans, privacy of MACs, delete-my-history."""
from pathlib import Path

import pytest

from netcheck import history
from netcheck.cli import main
from netcheck.core.analysis import Analysis, analyze_file
from netcheck.core.diff import compare
from netcheck.core.models import Host, Port, ScanResult
from netcheck.core.rules import evaluate, network_score

SYN = Path(__file__).parent / "fixtures" / "validation"


@pytest.fixture
def db(tmp_path):
    return tmp_path / "history.sqlite"


def _analysis(name, hosts, start=1_800_000_000):
    scan = ScanResult(source=name, hosts=hosts, start_time=start)
    findings = evaluate(scan)
    return Analysis(file=name, scan=scan, findings=findings, score=network_score(findings))


def test_changes_from_db_match_file_diff(db):
    before, after = analyze_file(SYN / "V6a_before.xml"), analyze_file(SYN / "V6b_after.xml")
    with history.open_history(db) as conn:
        history.save(conn, before)
        history.save(conn, after)
        ch = history.changes(conn)
    expected = compare(before, after)
    for k in expected:
        assert ch[k] == expected[k], k
    assert len(ch["resolved_findings"]) == 3
    assert (ch["score_before"], ch["score_after"]) == (60, 100)


def test_full_mac_never_written_to_disk(db):
    a = analyze_file(SYN / "V6a_before.xml")
    macs = [h.mac for h in a.scan.hosts if h.mac]
    assert macs
    with history.open_history(db) as conn:
        history.save(conn, a)
        stored = [r["masked_mac"] for r in conn.execute("SELECT masked_mac FROM devices")]
    raw = b"".join(p.read_bytes() for p in db.parent.iterdir())
    for mac in macs:
        assert mac.upper().encode() not in raw.upper()
        assert mac.replace(":", "").upper().encode() not in raw.upper()
    assert all(m.startswith("XX:XX:XX:XX:") for m in stored if m)


def test_same_vendor_devices_stay_distinct(db):
    # Two cameras from the same vendor have the same masked MAC; identity must still differ.
    cam = lambda ip, mac: Host(ip=ip, mac=mac, vendor="Hikvision",
                               ports=[Port("tcp", 554, "open", "rtsp")])
    one = _analysis("a.xml", [cam("192.168.1.40", "44:19:B6:00:00:01")])
    two = _analysis("b.xml", [cam("192.168.1.40", "44:19:B6:00:00:01"),
                              cam("192.168.1.41", "44:19:B6:00:00:02")], start=1_800_000_100)
    with history.open_history(db) as conn:
        history.save(conn, one)
        history.save(conn, two)
        ch = history.changes(conn)
    assert ch["new_devices"] == ["192.168.1.41"]
    assert ch["alerts"] is True


def test_device_keeps_identity_when_ip_changes(db):
    h = lambda ip: Host(ip=ip, mac="B8:27:EB:00:00:30", vendor="Raspberry Pi Foundation")
    with history.open_history(db) as conn:
        history.save(conn, _analysis("a.xml", [h("192.168.1.30")]))
        history.save(conn, _analysis("b.xml", [h("192.168.1.77")], start=1_800_000_100))
        ch = history.changes(conn)
    assert ch["new_devices"] == [] and ch["removed_devices"] == []


def test_trend_order_duplicates_and_unreadable(db):
    with history.open_history(db) as conn:
        late = analyze_file(SYN / "V6b_after.xml")
        assert history.save(conn, late)[1] is True
        assert history.save(conn, late)[1] is False          # same file saved twice -> ignored
        broken = analyze_file(SYN / "V7_broken.xml")
        with pytest.raises(ValueError):
            history.save(conn, broken)
        rows = history.trend(conn)
    assert len(rows) == 1 and rows[0]["network_score"] == 100


def test_cascade_removes_child_rows(db):
    with history.open_history(db) as conn:
        history.save(conn, analyze_file(SYN / "V6a_before.xml"))
        conn.execute("DELETE FROM scans")
        for table in ("devices", "ports", "findings"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_cli_add_list_changes_delete(db, capsys):
    assert main(["history", "add", str(SYN / "V6a_before.xml"), str(SYN / "V6b_after.xml"), "--db", str(db)]) == 0
    assert main(["history", "list", "--db", str(db)]) == 0
    assert main(["history", "changes", "--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert '"score_change": 40' in out
    assert main(["history", "delete", "--yes", "--db", str(db)]) == 0
    assert not db.exists()
    assert main(["history", "changes", "--db", str(db)]) == 1   # empty again


def _router(*ports):
    return Host(ip="192.168.1.1", mac="50:C7:BF:11:22:33", vendor="TP-Link", ports=list(ports))


def test_http_to_https_is_a_fix_not_an_alert():
    from netcheck.core.diff import compare
    ch = compare(analyze_file(SYN / "V6a_before.xml"), analyze_file(SYN / "V6b_after.xml"))
    assert ch["secured_ports"] == [{"ip": "192.168.1.1", "service": "http", "from_port": 80,
                                    "to_port": 443, "protocol": "tcp"}]
    assert ch["new_port_alerts"] == [] and ch["alerts"] is False
    assert [p["port"] for p in ch["opened_ports"]] == [443]        # still reported as a fact


def test_telnet_to_ssh_is_a_fix():
    from netcheck.core.diff import compare
    before = _analysis("a.xml", [_router(Port("tcp", 23, "open", "telnet"))])
    after = _analysis("b.xml", [_router(Port("tcp", 22, "open", "ssh"))], start=1_800_000_100)
    ch = compare(before, after)
    assert ch["secured_ports"][0]["to_port"] == 22 and ch["alerts"] is False


def test_unrelated_new_port_still_alerts():
    from netcheck.core.diff import compare
    before = _analysis("a.xml", [_router(Port("tcp", 80, "open", "http"))])
    after = _analysis("b.xml", [_router(Port("tcp", 443, "open", "http", tunnel="ssl"),
                                        Port("tcp", 3389, "open", "ms-wbt-server"))], start=1_800_000_100)
    ch = compare(before, after)
    assert [p["port"] for p in ch["new_port_alerts"]] == [3389]
    assert ch["alerts"] is True


def test_old_database_without_tls_column_is_upgraded(db):
    import sqlite3
    old = sqlite3.connect(db)
    old.executescript(history.SCHEMA.replace(",\n    tls      INTEGER NOT NULL DEFAULT 0", ""))
    old.close()
    with history.open_history(db) as conn:
        history.save(conn, analyze_file(SYN / "V6a_before.xml"))
        assert conn.execute("SELECT COUNT(*) FROM ports WHERE tls = 0").fetchone()[0] > 0


def test_history_folder_and_file_are_owner_only(tmp_path):
    import os, stat
    db = tmp_path / "private" / "history.sqlite"
    with history.open_history(db):
        pass
    if os.name == "posix":
        assert stat.S_IMODE(db.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(db.stat().st_mode) == 0o600


def test_private_mac_change_is_the_same_device():
    """Phones/laptops rotate private MACs: same IP + new MAC is not 'one gone, one new'."""
    from netcheck.core.diff import compare
    ch = compare(analyze_file(SYN / "V6a_before.xml"), analyze_file(SYN / "V6b_after.xml"))
    assert ch["new_devices"] == [] and ch["removed_devices"] == []
    assert len(ch["resolved_findings"]) == 3 and (ch["score_before"], ch["score_after"]) == (60, 100)


def test_really_new_device_is_still_reported():
    from netcheck.core.diff import compare
    before = _analysis("a.xml", [_router(Port("tcp", 80, "open", "http"))])
    extra = Host(ip="192.168.1.77", mac="AA:BB:CC:DD:EE:01", vendor="Acme", hostnames=["cam"],
                 ports=[Port("tcp", 554, "open", "rtsp")])
    after = _analysis("b.xml", [_router(Port("tcp", 80, "open", "http")), extra], start=1_800_000_100)
    ch = compare(before, after)
    assert ch["new_devices"] == ["192.168.1.77"] and ch["alerts"] is True
