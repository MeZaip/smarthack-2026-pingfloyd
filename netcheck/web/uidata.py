"""The data object behind ui/ (window.NETCHECK_DATA), built from the real analyser.

Used two ways:
  * tools/export_ui_data.py writes it once into ui/data.js (the online demo, example networks only);
  * the desktop app (netcheck.web.server) builds it live from the user's own scans and history.
MAC addresses are masked by Analysis.devices() (NFR-02); nothing here talks to the network.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .. import history
from ..core.analysis import analyze_file, scan_files_in
from ..core.device import DEVICE_LABELS
from ..explain.simple_texts import GLOSSARY, SIMPLE, WHO
from ..explain.texts import LANGS, SEVERITY_LABELS, TEXTS, score_band

# Inside the packaged app (PyInstaller) the bundled files live in sys._MEIPASS.
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
EXAMPLES = ROOT / "tests" / "fixtures" / "synthetic"


def scan_entry(path: Path, label: Optional[str] = None) -> dict:
    a = analyze_file(path)
    if not a.ok:
        return {"file": label or a.file, "error": a.error}
    return {
        "file": label or a.file,
        "score": a.score,
        "band": score_band(a.score)["color"],
        "devices": a.devices(),
        "findings": [
            {"ip": f.ip, "port": f.port, "protocol": f.protocol, "code": f.code,
             "severity": f.severity, "points": f.points, "evidence": f.evidence}
            for f in a.prioritized()
        ],
    }


def history_entry(before: Path, after: Path) -> dict:
    """Score trend + before/after of two scan files, through a throw-away history database."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "history.sqlite"
        with history.open_history(db) as conn:
            for f in (before, after):
                history.save(conn, analyze_file(f))
            return {"trend": history.trend(conn), "changes": history.changes(conn)}


def _static_parts() -> dict:
    return {
        "texts": {code: {**{lang: t[lang] for lang in LANGS}, "refs": t.get("refs", [])}
                  for code, t in TEXTS.items()},
        "simple": SIMPLE,
        "who": WHO,
        "glossary": {lang: [{"term": a, "meaning": b} for a, b in items] for lang, items in GLOSSARY.items()},
        "severity": SEVERITY_LABELS,
        "deviceLabels": DEVICE_LABELS,
    }


def demo_data(folder: Path = EXAMPLES, before: Optional[Path] = None, after: Optional[Path] = None) -> dict:
    """Example networks only (what the online demo shows)."""
    before = before or EXAMPLES / "V6a_before.xml"
    after = after or EXAMPLES / "V6b_after.xml"
    return {"mode": "demo", "scans": [scan_entry(f) for f in scan_files_in(folder)],
            "history": history_entry(before, after), **_static_parts()}


def live_data(scans_dir: Path, db: Optional[str] = None, examples: Path = EXAMPLES) -> dict:
    """The user's own scans (newest first), then the examples; history comes from the real database.
    If the user has fewer than two saved scans, the history tab shows the example before/after."""
    own = sorted(Path(scans_dir).glob("scan_*.xml"), reverse=True) if Path(scans_dir).is_dir() else []
    scans = [scan_entry(f, label=f"My network · {f.stem[5:].replace('_', ' ')}") for f in own]
    scans += [scan_entry(f, label=f"Example · {f.stem}") for f in scan_files_in(examples)]
    hist, real = None, False
    if history.db_path(db).exists():
        with history.open_history(db) as conn:
            changes = history.changes(conn)
            if changes:
                hist, real = {"trend": history.trend(conn), "changes": changes}, True
    if hist is None:
        hist = history_entry(examples / "V6a_before.xml", examples / "V6b_after.xml")
    return {"mode": "app", "own_scans": len(own), "history_is_example": not real,
            "scans": scans, "history": hist, **_static_parts()}


def to_js(data: dict) -> str:
    """window.NETCHECK_DATA = {...}; safe to put inside a <script> (no "</" sequences)."""
    body = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f"window.NETCHECK_DATA = {body};\n"
