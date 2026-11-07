"""Local scan history in SQLite: score trend + before/after between saved scans (FR-10, FR-13, NFR-02).

Privacy by design:
* The full MAC address is never written to disk. We store the masked MAC
  (vendor prefix only, for display) and a keyed hash of the full MAC used only
  to recognise the same device across scans. The hash key is random per
  history file, so it is useless outside this machine and is destroyed
  together with the history.
* The database lives outside the repository by default (~/.netcheck/), is
  created with owner-only permissions, and `delete_history` removes the file
  itself (not just the rows, which SQLite could leave in free pages).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Optional

from .core.analysis import Analysis
from .core.device import guess_type, mask_mac
from .core.diff import Snapshot, compare_snapshots
from .core.models import Host

DEFAULT_DB = Path.home() / ".netcheck" / "history.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scans (
    scan_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    file          TEXT    NOT NULL,
    scanned_at    INTEGER,            -- nmap start time (unix), may be missing
    saved_at      INTEGER NOT NULL,
    network_score INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
    device_id   INTEGER PRIMARY KEY,
    scan_id     INTEGER NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    device_key  TEXT    NOT NULL,     -- keyed hash of the full MAC, or "ip:<ip>" when nmap saw no MAC
    ip          TEXT    NOT NULL,
    masked_mac  TEXT,
    vendor      TEXT,
    hostname    TEXT,
    device_type TEXT    NOT NULL,
    UNIQUE (scan_id, device_key)
);
CREATE TABLE IF NOT EXISTS ports (
    scan_id  INTEGER NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    ip       TEXT    NOT NULL,
    protocol TEXT    NOT NULL,
    port     INTEGER NOT NULL,
    service  TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS findings (
    finding_id   INTEGER PRIMARY KEY,
    scan_id      INTEGER NOT NULL REFERENCES scans(scan_id) ON DELETE CASCADE,
    ip           TEXT    NOT NULL,
    port         INTEGER,             -- NULL for device-level findings
    protocol     TEXT,
    finding_code TEXT    NOT NULL,
    severity     TEXT    NOT NULL,
    points       INTEGER NOT NULL,
    evidence     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_devices_scan  ON devices(scan_id);
CREATE INDEX IF NOT EXISTS idx_ports_scan    ON ports(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
"""

# Chronological order: when the scan was taken, then insertion order as tie-break.
_ORDER = "COALESCE(scanned_at, saved_at), scan_id"


def db_path(path: Optional[str | os.PathLike] = None) -> Path:
    return Path(path or os.environ.get("NETCHECK_DB") or DEFAULT_DB)


def connect(path: Optional[str | os.PathLike] = None) -> sqlite3.Connection:
    p = db_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.touch(mode=0o600)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # off by default in SQLite; needed for ON DELETE CASCADE
    conn.executescript(SCHEMA)
    return conn


def _salt(conn: sqlite3.Connection) -> bytes:
    row = conn.execute("SELECT value FROM meta WHERE key = 'device_salt'").fetchone()
    if row:
        return bytes.fromhex(row["value"])
    salt = secrets.token_bytes(16)
    conn.execute("INSERT INTO meta (key, value) VALUES ('device_salt', ?)", (salt.hex(),))
    return salt


def _key_fn(salt: bytes):
    def key(host: Host) -> str:
        mac = (host.mac or "").replace("-", ":").upper()
        if not mac:
            return f"ip:{host.ip}"
        return hmac.new(salt, mac.encode(), hashlib.sha256).hexdigest()[:20]
    return key


def save(conn: sqlite3.Connection, a: Analysis) -> tuple[int, bool]:
    """Store one analysed scan. Returns (scan_id, created). Unreadable scans are rejected."""
    if not a.ok:
        raise ValueError(f"{a.file} is not readable: {a.error}")
    with conn:
        dup = conn.execute(
            "SELECT scan_id FROM scans WHERE file = ? AND scanned_at IS ?",
            (a.file, a.scan.start_time),
        ).fetchone()
        if dup:
            return dup["scan_id"], False

        key = _key_fn(_salt(conn))
        cur = conn.execute(
            "INSERT INTO scans (file, scanned_at, saved_at, network_score) VALUES (?, ?, ?, ?)",
            (a.file, a.scan.start_time, int(time.time()), a.score),
        )
        scan_id = cur.lastrowid
        hosts = a.scan.up_hosts
        conn.executemany(
            "INSERT OR IGNORE INTO devices (scan_id, device_key, ip, masked_mac, vendor, hostname, device_type)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(scan_id, key(h), h.ip, mask_mac(h.mac), h.vendor, h.hostname, guess_type(h)) for h in hosts],
        )
        conn.executemany(
            "INSERT INTO ports (scan_id, ip, protocol, port, service) VALUES (?, ?, ?, ?, ?)",
            [(scan_id, h.ip, p.protocol, p.portid, p.service) for h in hosts for p in h.open_ports],
        )
        conn.executemany(
            "INSERT INTO findings (scan_id, ip, port, protocol, finding_code, severity, points, evidence)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(scan_id, f.ip, f.port, f.protocol, f.code, f.severity, f.points, f.evidence) for f in a.findings],
        )
    return scan_id, True


def trend(conn: sqlite3.Connection) -> list[dict]:
    """All saved scans, oldest first, with score and number of findings."""
    rows = conn.execute(
        "SELECT s.scan_id, s.file, s.scanned_at, s.saved_at, s.network_score,"
        " (SELECT COUNT(*) FROM findings f WHERE f.scan_id = s.scan_id) AS findings,"
        " (SELECT COUNT(*) FROM devices d WHERE d.scan_id = s.scan_id) AS devices"
        f" FROM scans s ORDER BY {_ORDER}"
    ).fetchall()
    return [dict(r) for r in rows]


def load_snapshot(conn: sqlite3.Connection, scan_id: int) -> Snapshot:
    s = conn.execute("SELECT file, network_score FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
    if not s:
        raise KeyError(f"no saved scan with id {scan_id}")
    devices = {r["device_key"]: r["ip"] for r in
               conn.execute("SELECT device_key, ip FROM devices WHERE scan_id = ?", (scan_id,))}
    ports = frozenset((r["ip"], r["protocol"], r["port"], r["service"]) for r in
                      conn.execute("SELECT ip, protocol, port, service FROM ports WHERE scan_id = ?", (scan_id,)))
    findings = frozenset((r["ip"], r["port"], r["finding_code"]) for r in
                         conn.execute("SELECT ip, port, finding_code FROM findings WHERE scan_id = ?", (scan_id,)))
    return Snapshot(file=s["file"], score=s["network_score"], devices=devices,
                    open_ports=ports, findings=findings)


def changes(conn: sqlite3.Connection, before_id: Optional[int] = None,
            after_id: Optional[int] = None) -> Optional[dict]:
    """Before/after between two saved scans; by default the last two. None if fewer than two exist."""
    if before_id is None or after_id is None:
        ids = [r["scan_id"] for r in conn.execute(f"SELECT scan_id FROM scans ORDER BY {_ORDER}")]
        if len(ids) < 2:
            return None
        before_id, after_id = ids[-2], ids[-1]
    result = compare_snapshots(load_snapshot(conn, before_id), load_snapshot(conn, after_id))
    return {"before_scan_id": before_id, "after_scan_id": after_id, **result}


def delete_history(path: Optional[str | os.PathLike] = None) -> bool:
    """One-click 'Delete my history': removes the database file and its journals. True if anything was deleted."""
    p = db_path(path)
    removed = False
    for f in (p, p.with_name(p.name + "-wal"), p.with_name(p.name + "-shm"), p.with_name(p.name + "-journal")):
        if f.exists():
            f.unlink()
            removed = True
    return removed


def open_history(path: Optional[str | os.PathLike] = None):
    """`with open_history() as conn:` closes the connection afterwards."""
    return closing(connect(path))
