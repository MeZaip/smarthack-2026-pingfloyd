"""Web UI (FR-11) on top of the core engine and the local history.

Local only (127.0.0.1), runs unprivileged (NFR-04). Jinja2 autoescape is ON, so banners,
titles and hostnames from hostile scan files can't inject HTML (NFR-03).
Findings and scores come only from netcheck.core; the AI assistant (netcheck.ai) answers
questions and falls back to built-in text when the gateway is unavailable.
"""
from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import history
from ..ai.assistant import ask as ai_ask
from ..core.analysis import Analysis
from ..core.parser import MAX_FILE_BYTES, ScanFileError, parse_bytes
from ..core.rules import evaluate, network_score
from .api import router as api_router
from .house import rooms
from .i18n import UI
from .views import Explain, alerts, scan_view

app = FastAPI(title="NetCheck", docs_url=None, redoc_url=None)
app.include_router(api_router)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.autoescape = True

_flash: dict[str, dict] = {}
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


def _lang(request: Request) -> str:
    lang = request.query_params.get("lang") or request.cookies.get("lang") or "ro"
    return lang if lang in ("ro", "en") else "ro"


def _ctx(request: Request, lang: str, **kw) -> dict:
    return {"request": request, "lang": lang, "t": UI[lang], "ex": Explain, "scan_id": None, **kw}


def _render(request: Request, name: str, ctx: dict) -> HTMLResponse:
    resp = templates.TemplateResponse(request, name, ctx)
    resp.set_cookie("lang", ctx["lang"], samesite="strict", httponly=True)
    return resp


def _when(row: dict) -> str:
    ts = row.get("scanned_at") or row.get("saved_at")
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "—"


def _scan_list(conn) -> list[dict]:
    return [{**s, "when": _when(s)} for s in history.trend(conn)]


# ------------------------------------------------------------------ pages
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, id: Optional[int] = None, flash: Optional[str] = None):
    lang = _lang(request)
    with history.open_history() as conn:
        ids = history.scan_ids(conn)
        sid = id if id in ids else (ids[-1] if ids else None)
        r = changes = None
        if sid is not None:
            r = scan_view(get_analysis(conn, sid), lang)
            prev = history.previous_id(conn, sid)
            changes = history.changes(conn, prev, sid) if prev is not None else None
        scans = _scan_list(conn)
    return _render(request, "dashboard.html", _ctx(
        request, lang, r=r, scan_id=sid, dev=r.most_dangerous if r else None, first=r.first_fix if r else None,
        findings=r.findings if r else [], anchors=_anchors(r), diff=changes, alerts=alerts(changes, lang),
        scans=scans[-30:], rooms=rooms(r, lang), dev_by_ip={d.ip: d for d in (r.devices if r else [])},
        flash=_flash.pop(flash, None) if flash else None))


def _anchors(r) -> dict[int, str]:
    """Index of the first finding of each device -> its IP (target of the '#dev-<ip>' links)."""
    out, seen = {}, set()
    for i, f in enumerate(r.findings if r else []):
        if f.ip not in seen:
            out[i] = f.ip
            seen.add(f.ip)
    return out


@app.post("/upload")
async def upload(request: Request, files: list[UploadFile] = File(...)):
    lang = _lang(request)
    t = UI[lang]
    last_id, errors = None, []
    with history.open_history() as conn:
        for f in files:
            data = await f.read(MAX_FILE_BYTES + 1)
            name = Path(f.filename or "upload.xml").name[:120]
            a = analyze_bytes(data, name)
            if not a.ok:
                errors.append(f"{name}: {a.error}")
                continue
            last_id, _created = history.save(conn, a)
            _remember(last_id, a)
    url = f"/?lang={lang}" + (f"&id={last_id}" if last_id is not None else "")
    if errors:
        token = secrets.token_urlsafe(8)
        _flash[token] = {"status": "error", "text": f"✖ {t['error_title']}",
                         "where": " · ".join(errors), "evidence": None, "help": t["error_help"]}
        url += f"&flash={token}#flash"
    return RedirectResponse(url, status_code=303)


@app.post("/ask", response_class=HTMLResponse)
def ask(request: Request, question: str = Form(...), scan_id: Optional[int] = Form(None)):
    lang = _lang(request)
    question = question.strip()[:500]
    with history.open_history() as conn:
        ids = history.scan_ids(conn)
        sid = scan_id if scan_id in ids else (ids[-1] if ids else None)
        if sid is None:
            return _render(request, "answer.html", _ctx(request, lang, question=question,
                                                        answer=UI[lang]["no_scan"], mode="offline"))
        a = get_analysis(conn, sid)
        prev = history.previous_id(conn, sid)
        previous = get_analysis(conn, prev) if prev is not None else None
    ans = ai_ask(question, a, lang, previous)
    mode = "ai" if ans.source == "ai" else ("rejected" if (ans.reason or "").startswith("grounding") else "offline")
    return _render(request, "answer.html", _ctx(request, lang, question=question, answer=ans.text,
                                                mode=mode, scan_id=sid))


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    lang = _lang(request)
    with history.open_history() as conn:
        scans = _scan_list(conn)
        diffs = [(a, b, history.changes(conn, a["scan_id"], b["scan_id"])) for a, b in zip(scans, scans[1:])]
    return _render(request, "history.html", _ctx(request, lang, scans=scans, diffs=diffs[::-1],
                                                 alerts_of=lambda d: alerts(d, lang)))


@app.post("/history/delete")
def delete_history(request: Request):
    history.delete_history()
    _cache.clear()
    return RedirectResponse(f"/history?lang={_lang(request)}", status_code=303)


@app.get("/report/{scan_id}", response_class=HTMLResponse)
def report(request: Request, scan_id: int):
    lang = _lang(request)
    with history.open_history() as conn:
        try:
            r = scan_view(get_analysis(conn, scan_id), lang)
        except KeyError:
            r = None
    return _render(request, "report.html", _ctx(
        request, lang, r=r, scan_id=scan_id, dev=r.most_dangerous if r else None,
        first=r.first_fix if r else None, findings=r.findings if r else []))
