"""Web UI (FR-11). Local only (127.0.0.1), runs unprivileged (NFR-04).
Jinja2 autoescape is ON, so banners/titles/nicknames can't inject HTML (NFR-03)."""
from __future__ import annotations

import json
import secrets
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import certificate, explain, history, verify
from ..analyzer import analyze_bytes, most_dangerous, ranked_findings
from ..assistant import Assistant, Session
from ..models import Host
from ..parser import MAX_FILE_BYTES
from .house import display_name, rooms
from .i18n import UI

app = FastAPI(title="NetCheck", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.autoescape = True

_assistants: dict[tuple[int, str], Assistant] = {}
_flash: dict[str, dict] = {}
MAX_CERT_BYTES = 1_000_000


def _lang(request: Request) -> str:
    lang = request.query_params.get("lang") or request.cookies.get("lang") or "ro"
    return lang if lang in ("ro", "en") else "ro"


def _ctx(request: Request, lang: str, **kw) -> dict:
    return {"request": request, "lang": lang, "t": UI[lang], "ex": explain, **kw}


def _render(request: Request, name: str, ctx: dict) -> HTMLResponse:
    resp = templates.TemplateResponse(request, name, ctx)
    resp.set_cookie("lang", ctx["lang"], samesite="strict", httponly=True)
    return resp


def _first_and_last_ok(source: str) -> tuple[int | None, int | None]:
    ok = [s for s in history.list_scans(source) if s["ok"]]
    return (ok[0]["id"], ok[-1]["id"]) if len(ok) >= 2 else (None, None)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, id: int | None = None, flash: str | None = None):
    lang = _lang(request)
    scan_id = id or history.latest_id()
    r = history.load(scan_id) if scan_id else None
    dev = first = diff = alerts = None
    nick = history.nicknames()
    ver = history.verifications_for(scan_id) if scan_id else {}
    est = None
    if r and r.ok:
        dev, first = most_dangerous(r)
        prev = history.previous_of(scan_id)
        if prev:
            diff = history.diff(history.load(prev), r)
            alerts = history.alerts(diff, lang)
        est = verify.estimated_score(r.score, r.findings, ver)
    meta = next((s for s in history.list_scans() if s["id"] == scan_id), None)
    cert_pair = _first_and_last_ok(meta["source"]) if meta else (None, None)
    findings = ranked_findings(r) if r and r.ok else []
    anchors, seen = {}, set()
    for i, f in enumerate(findings):
        if f.ip not in seen:
            anchors[i] = f.ip
            seen.add(f.ip)
    return _render(request, "dashboard.html", _ctx(
        request, lang, r=r, scan_id=scan_id, dev=dev, first=first, findings=findings, anchors=anchors,
        diff=diff, alerts=alerts, scans=history.list_scans()[-30:], rooms=rooms(r, nick, ver, lang),
        nick=nick, dev_by_ip={d.ip: d for d in (r.devices if r and r.ok else [])},
        name_of=lambda d: display_name(d, nick, lang), ver=ver, est=est,
        flash=_flash.pop(flash, None) if flash else None,
        watch_events=history.watch_events(5), watch_last=history.kv_get("watch:last_check"),
        cert_pair=cert_pair))


@app.post("/upload")
async def upload(request: Request, files: list[UploadFile] = File(...)):
    last_id = None
    batch = len(files) > 1
    for f in files:
        data = await f.read(MAX_FILE_BYTES + 1)
        name = Path(f.filename or "upload.xml").name[:120]
        res = analyze_bytes(data, name)
        last_id = history.save(res, source="upload-batch" if batch else "lab")
    lang = _lang(request)
    if batch:
        return RedirectResponse(f"/batch?lang={lang}", status_code=303)
    return RedirectResponse(f"/?id={last_id}&lang={lang}", status_code=303)


@app.post("/device/name")
def set_name(request: Request, device_id: str = Form(...), name: str = Form(""), scan_id: int = Form(...)):
    if len(device_id) == 12 and all(c in "0123456789abcdef" for c in device_id):
        history.set_nickname(device_id, name)
    return RedirectResponse(f"/?id={scan_id}&lang={_lang(request)}#house", status_code=303)


@app.post("/verify")
def verify_finding(request: Request, scan_id: int = Form(...), ip: str = Form(...), port: int = Form(...),
                   code: str = Form(...), consent: str | None = Form(None)):
    lang = _lang(request)
    t = UI[lang]
    r = history.load(scan_id)
    f = next((x for x in (r.findings if r and r.ok else []) if x.ip == ip and x.port == port and x.code == code), None)
    if f is None:
        msg = {"status": "error", "text": t["verify_unknown"]}
    elif not consent:
        msg = {"status": "refused", "text": t["verify_need_consent"]}
    else:
        d = next(x for x in r.devices if x.ip == ip)
        res = verify.verify(f, Host(ip=ip, vendor=d.vendor, hostname=d.hostname), scan_id=scan_id,
                            device_id=d.device_id)
        msg = {"status": res.status, "text": res.message(lang), "evidence": res.evidence,
               "where": f"{display_name(d, history.nicknames(), lang)} ({ip}:{port})"}
    token = secrets.token_urlsafe(8)
    _flash[token] = msg
    return RedirectResponse(f"/?id={scan_id}&lang={lang}&flash={token}#flash", status_code=303)


@app.get("/batch", response_class=HTMLResponse)
def batch(request: Request, source: str | None = None):
    lang = _lang(request)
    scans = history.list_scans()
    sources = sorted({s["source"] for s in scans})
    chosen = source or ("upload-batch" if "upload-batch" in sources else (sources[0] if sources else None))
    rows = [(s, history.load(s["id"])) for s in scans if s["source"] == chosen]
    return _render(request, "batch.html", _ctx(request, lang, rows=rows, sources=sources, chosen=chosen))


@app.post("/ask", response_class=HTMLResponse)
def ask(request: Request, question: str = Form(...), scan_id: int | None = Form(None)):
    lang = _lang(request)
    key = (scan_id or 0, lang)
    if key not in _assistants:
        s = Session(lang=lang, allow_live_scan=False)
        if scan_id:
            s.load_history(scan_id)
        _assistants[key] = Assistant(s)
    a = _assistants[key]
    reply = a.ask(question)
    provider = getattr(a.provider, "label", "") if a.provider else ""
    return _render(request, "answer.html", _ctx(request, lang, question=question, answer=reply,
                                                 mode=a.last_mode, provider=provider, scan_id=scan_id))


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, source: str = "lab"):
    lang = _lang(request)
    all_scans = history.list_scans()
    sources = sorted({s["source"] for s in all_scans}) or ["lab"]
    scans = [s for s in all_scans if s["source"] == source]
    diffs = []
    ok_scans = [s for s in scans if s["ok"]]
    for a, b in zip(ok_scans, ok_scans[1:]):
        d = history.diff(history.load(a["id"]), history.load(b["id"]))
        diffs.append((a, b, d, history.alerts(d, lang)))
    return _render(request, "history.html", _ctx(request, lang, scans=scans, diffs=diffs[::-1],
                                                  sources=sources, source=source,
                                                  cert_pair=_first_and_last_ok(source)))


@app.post("/history/delete")
def delete_history(request: Request):
    history.delete_all()
    _assistants.clear()
    return RedirectResponse(f"/history?lang={_lang(request)}", status_code=303)


@app.get("/report/{scan_id}", response_class=HTMLResponse)
def report(request: Request, scan_id: int):
    lang = _lang(request)
    r = history.load(scan_id)
    dev, first = most_dangerous(r) if r and r.ok else (None, None)
    return _render(request, "report.html", _ctx(request, lang, r=r, dev=dev, first=first,
                                                 findings=ranked_findings(r) if r and r.ok else []))


@app.get("/certificate", response_class=HTMLResponse)
def certificate_page(request: Request, before: int, after: int):
    lang = _lang(request)
    metas = {s["id"]: s for s in history.list_scans()}
    b, a = history.load(before), history.load(after)
    if not (b and a and b.ok and a.ok):
        return _render(request, "certificate.html", _ctx(request, lang, cert=None))
    cert = certificate.build(b, a, metas[before]["created_at"], metas[after]["created_at"])
    return _render(request, "certificate.html", _ctx(
        request, lang, cert=cert, p=cert["payload"], cert_json=json.dumps(cert, ensure_ascii=False, indent=2)))


@app.get("/certificate/verify", response_class=HTMLResponse)
def cert_verify_form(request: Request):
    return _render(request, "cert_verify.html", _ctx(request, _lang(request), result=None))


@app.post("/certificate/verify", response_class=HTMLResponse)
async def cert_verify(request: Request, file: UploadFile = File(...)):
    lang = _lang(request)
    raw = await file.read(MAX_CERT_BYTES + 1)
    try:
        if len(raw) > MAX_CERT_BYTES:
            raise ValueError("too large")
        cert = json.loads(raw.decode("utf-8"))
        ok, reason, ours = certificate.verify(cert)
        payload = cert.get("payload", {}) if ok else None
    except (ValueError, UnicodeDecodeError, AttributeError):
        ok, reason, ours, payload = False, "not a valid JSON file", False, None
    return _render(request, "cert_verify.html", _ctx(request, lang, result={
        "ok": ok, "reason": reason, "ours": ours, "payload": payload}))
