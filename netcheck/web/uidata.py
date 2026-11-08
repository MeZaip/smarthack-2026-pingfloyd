"""Data for the SafeHouse UI (ui/), built live from the local history.

`ui/app.js` reads one object, `window.NETCHECK_DATA`. For the offline demo it comes from
tools/export_ui_data.py (fixed example files); in the app it comes from here: the scans saved on
this computer (live checks and uploaded files), analysed by the same core as the CLI.
MAC addresses are masked by Analysis.devices() (NFR-02); nothing here is sent anywhere.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Callable, Optional

from .. import history
from ..ai.guide import vendor_for, vendor_name
from ..core.analysis import Analysis
from ..core.device import DEVICE_LABELS
from ..explain.simple_texts import GLOSSARY, SIMPLE, WHO
from ..explain.texts import LANGS, SEVERITY_LABELS, TEXTS, score_band

MAX_SCANS = 100         # newest scans with full details in the page (all of them are listed in Results)
_LIVE_FILE = re.compile(r"^scan_\d{8}_\d{6}\.xml$")


def static_part() -> dict:
    """Texts the UI needs (same keys as tools/export_ui_data.py)."""
    return {
        "texts": {code: {**{lang: t[lang] for lang in LANGS}, "refs": t.get("refs", [])}
                  for code, t in TEXTS.items()},
        "simple": SIMPLE,
        "who": WHO,
        "glossary": {lang: [{"term": a, "meaning": b} for a, b in items] for lang, items in GLOSSARY.items()},
        "severity": SEVERITY_LABELS,
        "deviceLabels": DEVICE_LABELS,
    }


def _when(row: dict) -> str:
    ts = row.get("scanned_at") or row.get("saved_at")
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M") if ts else ""


def label_of(row: dict) -> str:
    """'07.11.2026 17:20' for a live check, 'my_scan.xml · 07.11.2026 17:20' for an uploaded file."""
    when = _when(row)
    if _LIVE_FILE.match(row["file"]):
        return when or row["file"]
    return f"{row['file']} · {when}" if when else row["file"]


def scan_entry(a: Analysis, row: dict, changes: Optional[dict], me_ip: Optional[str]) -> dict:
    devices = a.devices()
    for d in devices:
        d["me"] = bool(me_ip) and d["ip"] == me_ip
        maker = vendor_for(d)
        d["guide"] = vendor_name(maker) if maker else None     # "steps for your <maker>" is offered
    return {
        "scan_id": row["scan_id"],
        "file": a.file,
        "label": label_of(row),
        "when": _when(row),
        "score": a.score,
        "band": score_band(a.score)["color"],
        "devices": devices,
        "findings": [
            {"ip": f.ip, "port": f.port, "protocol": f.protocol, "code": f.code,
             "severity": f.severity, "points": f.points, "evidence": f.evidence}
            for f in a.prioritized()
        ],
        "changes": changes,      # compared with the scan saved just before it (None for the first)
    }


def live_part(load: Callable[[object, int], Analysis], me_ip: Optional[str] = None,
              app_mode: bool = False) -> dict:
    """Files saved on this computer, newest first: readable scans with their change since the previous
    readable one, unreadable files with their error (shown as ERROR, like scores.csv)."""
    with history.open_history() as conn:
        trend = history.trend(conn)
        all_rows = history.entries(conn)
        order = [r["scan_id"] for r in trend]
        scans = []
        for row in reversed(all_rows[-MAX_SCANS:]):
            if row["error"]:
                scans.append({"scan_id": row["scan_id"], "file": row["file"], "label": label_of(row), "when": _when(row),
                              "error": row["error"], "devices": [], "findings": [], "changes": None})
                continue
            i = order.index(row["scan_id"])
            changes = history.changes(conn, order[i - 1], row["scan_id"]) if i > 0 else None
            try:
                a = load(conn, row["scan_id"])
            except KeyError:
                continue
            scans.append(scan_entry(a, row, changes, me_ip))
        last = history.changes(conn)
    return {"live": True, "app_mode": app_mode, "me": me_ip, "scans": scans,
            "history": {"trend": trend, "all": all_rows, "changes": last}}


def payload(load: Callable[[object, int], Analysis], me_ip: Optional[str] = None, app_mode: bool = False) -> dict:
    return {**live_part(load, me_ip, app_mode), **static_part()}


def as_script(data: dict) -> str:
    """`window.NETCHECK_DATA = {...};` - safe inside a <script> (no '</' sequences)."""
    body = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f"window.NETCHECK_DATA = {body};\n"
