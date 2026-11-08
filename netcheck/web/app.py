"""SafeHouse local agent: serves the SafeHouse UI (ui/) and the JSON APIs, on this computer only.

Local only (127.0.0.1), runs unprivileged (NFR-04). The page inserts scan text only as text, never as
HTML (NFR-03). Findings and scores come only from netcheck.core; the AI assistant (netcheck.ai) answers
questions and falls back to built-in text when the gateway is unavailable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import history
from ..core.analysis import Analysis
from ..core.parser import ScanFileError, parse_bytes
from ..core.rules import evaluate, network_score
from . import api_v1, uidata
from .api import router as api_router
from .security import LocalOnly

app = FastAPI(title="SafeHouse", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(LocalOnly)          # local host only + session cookie on every state-changing request
app.include_router(api_router)         # read-only history API (service_data_contracts.md §2/§4)
app.include_router(api_v1.router)      # actions the page asks the local agent to do

# The SafeHouse UI (ui/): served by this agent at "/", with live data instead of the demo ui/data.js.
UI_DIR = Path(__file__).resolve().parent.parent.parent / "ui"
NO_CACHE = {"Cache-Control": "no-store"}
for _sub in ("vendor", "assets"):
    if (UI_DIR / _sub).is_dir():
        app.mount(f"/{_sub}", StaticFiles(directory=str(UI_DIR / _sub)), name=f"ui-{_sub}")

_cache: dict[tuple[str, int], Analysis] = {}   # full analyses of scans uploaded in this process
MAX_CACHE = 50


# ------------------------------------------------------------------ helpers
def analyze_bytes(data: bytes, name: str) -> Analysis:
    """Same pipeline as core.analysis.analyze_file, for an uploaded file."""
    try:
        scan = parse_bytes(data, name)
    except ScanFileError as e:
        return Analysis(file=name, error=str(e))
    except Exception as e:  # never crash on one bad file
        return Analysis(file=name, error=f"unexpected error: {e.__class__.__name__}")
    findings = evaluate(scan)
    return Analysis(file=name, scan=scan, findings=findings, score=network_score(findings))


def _db_key() -> str:
    return str(history.db_path())


def get_analysis(conn, scan_id: int) -> Analysis:
    """Full analysis if uploaded in this process, else rebuilt from the history rows. KeyError if unknown."""
    return _cache.get((_db_key(), scan_id)) or history.load_analysis(conn, scan_id)


def _remember(scan_id: int, a: Analysis) -> None:
    if len(_cache) >= MAX_CACHE:
        _cache.pop(next(iter(_cache)))
    _cache[(_db_key(), scan_id)] = a


api_v1.jobs._on_saved = _remember     # a live scan keeps its full analysis (banners, titles) for this session


_me = {"ip": None, "at": 0.0}


def this_ip() -> Optional[str]:
    """IP of the computer SafeHouse runs on (cached 30 s): shown as "this is your computer"."""
    import time
    from ..net import netdetect
    if time.time() - _me["at"] > 30:
        try:
            _me["ip"] = netdetect.detect().ip
        except Exception:  # noqa: BLE001 - no network is fine, just no highlight
            _me["ip"] = None
        _me["at"] = time.time()
    return _me["ip"]


def ui_data() -> dict:
    """window.NETCHECK_DATA for the SafeHouse UI, from the scans saved on this computer."""
    return uidata.payload(get_analysis, this_ip(), api_v1.life.app_mode)


# ------------------------------------------------------------------ SafeHouse UI (the app)
@app.get("/", include_in_schema=False)
def ui_index():
    return FileResponse(UI_DIR / "index.html", media_type="text/html", headers=NO_CACHE)


@app.get("/data.js", include_in_schema=False)
def ui_data_js():
    return Response(uidata.as_script(ui_data()), media_type="application/javascript", headers=NO_CACHE)


# registered last, so it never shadows the pages above
_UI_FILES = {"app.js": "application/javascript", "device3d.js": "application/javascript", "voice.js": "application/javascript",
             "safehouse3d.js": "application/javascript", "styles.css": "text/css"}


@app.get("/{name}", include_in_schema=False)
def ui_file(name: str):
    if name not in _UI_FILES:   # only these files: nothing else from the disk is reachable
        return Response("not found", status_code=404)
    return FileResponse(UI_DIR / name, media_type=_UI_FILES[name], headers=NO_CACHE)
