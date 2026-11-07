"""FR-10 history + FR-13 change alerts. Stored ONLY locally (NFR-02) in SQLite.

Raw MAC addresses are never stored — only the analysed ScanResult (masked MACs).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .identity import home_dir
from .models import ScanResult


def db_path() -> Path:
    return home_dir() / "history.db"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(db_path())
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS scans(
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, source TEXT NOT NULL,
        file TEXT NOT NULL, score INTEGER, ok INTEGER NOT NULL, data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS nicknames(device_id TEXT PRIMARY KEY, name TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS verifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, scan_id INTEGER, device_id TEXT,
        ip TEXT NOT NULL, port INTEGER, code TEXT NOT NULL, status TEXT NOT NULL, evidence TEXT);
    CREATE TABLE IF NOT EXISTS watch_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL,
        device_id TEXT, ip TEXT, detail TEXT);
    CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """)
    return c


# ---------------------------------------------------------------- nicknames ("Camera bebelușului")
MAX_NICK = 40


def set_nickname(dev_id: str, name: str) -> None:
    name = " ".join((name or "").split())[:MAX_NICK]
    with _conn() as c:
        if name:
            c.execute("INSERT INTO nicknames(device_id, name) VALUES(?,?) "
                      "ON CONFLICT(device_id) DO UPDATE SET name=excluded.name", (dev_id, name))
        else:
            c.execute("DELETE FROM nicknames WHERE device_id = ?", (dev_id,))


def nicknames() -> dict[str, str]:
    with _conn() as c:
        return {r["device_id"]: r["name"] for r in c.execute("SELECT device_id, name FROM nicknames")}


# ---------------------------------------------------------------- targeted re-checks ("Dovedește!")
def add_verification(scan_id: int | None, dev_id: str, ip: str, port: int | None, code: str,
                     status: str, evidence: str) -> None:
    with _conn() as c:
        c.execute("INSERT INTO verifications(ts, scan_id, device_id, ip, port, code, status, evidence) "
                  "VALUES (?,?,?,?,?,?,?,?)", (_now(), scan_id, dev_id, ip, port, code, status, evidence))


def verifications_for(scan_id: int) -> dict[tuple, dict]:
    """Latest verification per (ip, port, code) for this scan."""
    with _conn() as c:
        rows = c.execute("SELECT * FROM verifications WHERE scan_id = ? ORDER BY id", (scan_id,)).fetchall()
    return {(r["ip"], r["port"], r["code"]): dict(r) for r in rows}


# ---------------------------------------------------------------- watch mode ("Paznic")
def add_watch_event(kind: str, dev_id: str, ip: str, detail: str) -> None:
    with _conn() as c:
        c.execute("INSERT INTO watch_events(ts, kind, device_id, ip, detail) VALUES (?,?,?,?,?)",
                  (_now(), kind, dev_id, ip, detail))


def watch_events(limit: int = 20) -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM watch_events ORDER BY id DESC LIMIT ?", (limit,))]


def kv_get(key: str, default=None):
    with _conn() as c:
        r = c.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


def kv_set(key: str, value) -> None:
    with _conn() as c:
        c.execute("INSERT INTO kv(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, json.dumps(value)))


def save(result: ScanResult, source: str = "lab") -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO scans(created_at, source, file, score, ok, data) VALUES (?,?,?,?,?,?)",
            (_now(), source, result.file,
             result.score, int(result.ok), json.dumps(result.to_dict())),
        )
        return int(cur.lastrowid)


def list_scans(source: str | None = None) -> list[dict]:
    with _conn() as c:
        q = "SELECT id, created_at, source, file, score, ok FROM scans"
        args: tuple = ()
        if source:
            q += " WHERE source = ?"
            args = (source,)
        return [dict(r) for r in c.execute(q + " ORDER BY id", args)]


def load(scan_id: int) -> ScanResult | None:
    with _conn() as c:
        r = c.execute("SELECT data FROM scans WHERE id = ?", (scan_id,)).fetchone()
    return ScanResult.from_dict(json.loads(r["data"])) if r else None


def previous_of(scan_id: int) -> int | None:
    with _conn() as c:
        row = c.execute("SELECT source FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if not row:
            return None
        r = c.execute("SELECT id FROM scans WHERE source = ? AND id < ? AND ok = 1 ORDER BY id DESC LIMIT 1",
                      (row["source"], scan_id)).fetchone()
    return int(r["id"]) if r else None


def find_by_file(file: str, source: str | None = None) -> int | None:
    with _conn() as c:
        q, args = "SELECT id FROM scans WHERE file = ?", [file]
        if source:
            q += " AND source = ?"
            args.append(source)
        r = c.execute(q + " ORDER BY id DESC LIMIT 1", args).fetchone()
    return int(r["id"]) if r else None


def latest_id() -> int | None:
    with _conn() as c:
        r = c.execute("SELECT id FROM scans WHERE ok = 1 ORDER BY id DESC LIMIT 1").fetchone()
    return int(r["id"]) if r else None


def delete_all() -> None:
    """One-click 'delete my history' (NFR-02)."""
    p = db_path()
    if p.exists():
        p.unlink()


def diff(old: ScanResult, new: ScanResult) -> dict:
    old_dev = {d.ip: d for d in old.devices}
    new_dev = {d.ip: d for d in new.devices}

    def ports(r: ScanResult) -> set[tuple]:
        return {(d.ip, p["port"], p["protocol"], p["service"]) for d in r.devices for p in d.open_ports}

    def fkeys(r: ScanResult) -> dict:
        return {(f.ip, f.port, f.code): f for f in r.findings}

    of, nf = fkeys(old), fkeys(new)
    return {
        "old_file": old.file, "new_file": new.file,
        "old_score": old.score, "new_score": new.score,
        "score_delta": (new.score or 0) - (old.score or 0),
        "new_devices": [new_dev[ip].to_dict() for ip in sorted(set(new_dev) - set(old_dev))],
        "removed_devices": [old_dev[ip].to_dict() for ip in sorted(set(old_dev) - set(new_dev))],
        "opened_ports": sorted(ports(new) - ports(old), key=str),
        "closed_ports": sorted(ports(old) - ports(new), key=str),
        "resolved_findings": [of[k].to_dict() for k in sorted(set(of) - set(nf), key=str)],
        "new_findings": [nf[k].to_dict() for k in sorted(set(nf) - set(of), key=str)],
    }


def alerts(d: dict, lang: str = "ro") -> list[str]:
    """FR-13: new device / newly opened port since previous scan."""
    out = []
    for dev in d["new_devices"]:
        out.append(("Dispozitiv nou în rețea: " if lang == "ro" else "New device on the network: ")
                   + f"{dev['ip']} ({dev['vendor'] or dev['hostname'] or '?'})")
    for ip, port, proto, svc in d["opened_ports"]:
        out.append(("Port nou deschis: " if lang == "ro" else "Newly opened port: ")
                   + f"{ip} {port}/{proto} ({svc or '?'})")
    return out
