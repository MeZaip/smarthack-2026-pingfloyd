"""/api/v1: the actions the page can ask the local agent to do. The page is a thin client.

  GET    /api/v1/status              network we are on, Nmap installed?, AI online?, scan running?
  POST   /api/v1/scan                {"confirm": true} -> start a check of THIS network (202 + job)
  GET    /api/v1/scan/{job_id}       progress / result of a check
  POST   /api/v1/verify              {"scan_id", "ip", "port", "code"} -> re-check one fixed problem
  POST   /api/v1/ask                 {"question", "scan_id"?, "history"?} -> assistant answer (AI or built-in)
  POST   /api/v1/guide               {"scan_id", "ip", "code"} -> fix steps for that device's brand/model (AI + maker's site)
  GET    /api/v1/ui-data             everything the SafeHouse page shows (scans saved on this computer)
  POST   /api/v1/upload              one or more nmap XML files -> analysed and saved (broken ones: error)
  POST   /api/v1/export              nmap XML files (e.g. a whole folder) -> ZIP with findings.csv + scores.csv (FR-15)
  POST   /api/v1/export/history      the same two CSVs for the files saved on this computer (unreadable: ERROR)
  POST   /api/v1/report/{scan_id}    technical report of one saved check (.txt, nmap style, for an IT person)
  GET    /api/v1/guard               „Păzește casa": on/off, state, devices it knows, alerts for unknown devices
  POST   /api/v1/guard               {"on": true, "confirm": true} start guarding THIS network / {"on": false} stop
  POST   /api/v1/guard/ack           {"id", "mine"} "it is mine" / "I do not know it" for one event
  POST   /api/v1/guard/forget        forget the devices of this network (the guard learns it again)
  POST   /api/v1/guard/device        {"id", "action": "mine" | "stranger" | "forget"} for one known device
  DELETE /api/v1/history             delete my history (one click, NFR-02)
  POST   /api/v1/heartbeat           the open page is alive (app mode)
  POST   /api/v1/shutdown            "Close SafeHouse" (app mode)

Errors: {"error": {"code": "...", "message": "<plain words in the user's language>"}}.
All state-changing calls are protected by web/security.py (local host + session cookie + origin).
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional

from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from .. import history
from ..ai.assistant import ask as ai_ask
from ..ai.providers import LLMUnavailable, get_provider
from ..net import elevate, guardrail, netdetect, scanner
from ..net import verify as verify_mod
from . import agent

router = APIRouter(prefix="/api/v1", tags=["agent"])

jobs = agent.ScanJobs()
life = agent.AppLife()
guard = None                 # „Păzește casa" (netcheck.net.watch.Guard), created on first use


def _guard():
    global guard
    if guard is None:
        from ..net.watch import Guard
        every = os.environ.get("NETCHECK_GUARD_INTERVAL")          # default: 8 s on a hotspot-size network, else 20 s
        guard = Guard(interval=int(every) if every and every.isdigit() else None, busy=lambda: jobs.current() is not None)
    return guard


def _lang(request: Request) -> str:
    lang = request.query_params.get("lang") or request.cookies.get("lang") or "ro"
    return lang if lang in ("ro", "en") else "ro"


def _error(status: int, code: str, lang: str, message: Optional[str] = None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message or agent.message(code, lang)}}, status)


# ------------------------------------------------------------------ status
@router.get("/status")
def status(request: Request) -> dict:
    lang = _lang(request)
    with history.open_history() as conn:
        has_history = bool(history.scan_ids(conn))
    try:
        ai = get_provider().status()
    except Exception:  # noqa: BLE001
        ai = {"online": False}
    job = jobs.current()
    net = agent.network_info()
    if not net["ok"]:
        net["message"] = agent.message(net["code"], lang)
    return {
        "network": net,
        "nmap": scanner.find_nmap() is not None,
        "ai": {"online": bool(ai.get("online"))},
        "app_mode": life.app_mode,
        "has_history": has_history,
        "scan": job.to_dict(lang) if job else None,
    }


# ------------------------------------------------------------------ live scan
class ScanRequest(BaseModel):
    confirm: bool = False


@router.post("/scan", status_code=202)
def start_scan(body: ScanRequest, request: Request):
    lang = _lang(request)
    try:
        job = jobs.start(confirmed=body.confirm)
    except agent.ScanStartError as e:
        status_code = {"need_consent": 400, "busy": 409, "no_nmap": 503, "no_network": 503}.get(e.code, 400)
        return _error(status_code, e.code, lang)
    return job.to_dict(lang)


@router.get("/scan/{job_id}")
def scan_status(job_id: str, request: Request):
    job = jobs.get(job_id)
    if job is None:
        return _error(404, "not_found", _lang(request), "not found")
    return job.to_dict(_lang(request))


# ------------------------------------------------------------------ "I fixed it - check!"
class VerifyRequest(BaseModel):
    scan_id: int
    ip: str = Field(max_length=64)
    port: Optional[int] = Field(default=None, ge=0, le=65535)
    code: str = Field(max_length=40)


def _verify_runner(cmd: list[str]) -> bytes:
    """Run the unprivileged TCP re-check with the full nmap path (Windows) and no console window."""
    nmap = scanner.find_nmap()
    if not nmap or cmd[0] == "sudo":
        raise RuntimeError("nmap unavailable")
    kwargs = {"capture_output": True, "timeout": 120}
    if os.name == "nt":
        kwargs["creationflags"] = elevate.NO_WINDOW
    proc = subprocess.run([nmap] + cmd[1:], **kwargs)
    if proc.returncode != 0:
        raise RuntimeError("nmap failed")
    return proc.stdout


VERIFY_RESCAN = ("Pentru această problemă e nevoie de o verificare completă: apasă „Inspectează din nou”.",
                 "This problem needs a full check: press \"Inspect again\".")


@router.post("/verify")
def verify(body: VerifyRequest, request: Request):
    lang = _lang(request)
    from .app import get_analysis   # deferred: app imports this module
    with history.open_history() as conn:
        try:
            a = get_analysis(conn, body.scan_id)
        except KeyError:
            return _error(404, "not_found", lang, "scan not found")
    finding = next((f for f in a.findings if f.ip == body.ip and f.port == body.port and f.code == body.code), None)
    if finding is None:
        return _error(404, "not_found", lang, "Nu am găsit această problemă în scanare." if lang == "ro"
                      else "I could not find this problem in the scan.")
    try:
        net = netdetect.detect()
    except netdetect.NetworkDetectError:
        return _error(503, "no_network", lang)
    allow = guardrail.build_allowlist(net.subnet)
    host = next((h for h in a.scan.hosts if h.ip == finding.ip), None)
    res = verify_mod.verify(finding, host, allow, runner=_test_runner or _verify_runner)
    text = res.message(lang)
    if res.status in ("needs_root", "unsupported"):
        text = VERIFY_RESCAN[0] if lang == "ro" else VERIFY_RESCAN[1]
    elif res.status == "error":
        text = agent.message("scan_failed", lang)
    return {"status": res.status, "message": text, "evidence": res.evidence}


_test_runner = None   # tests inject a fake nmap here


# ------------------------------------------------------------------ assistant
class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=2000)


class AskRequest(BaseModel):
    question: str = Field(max_length=1000)
    scan_id: Optional[int] = None
    history: list[Turn] = Field(default_factory=list, max_length=12)
    style: str = Field(default="text", pattern="^(text|voice)$")   # voice: the answer is read aloud


@router.post("/ask")
def ask(body: AskRequest, request: Request):
    lang = _lang(request)
    from .app import get_analysis
    with history.open_history() as conn:
        ids = history.scan_ids(conn)
        sid = body.scan_id if body.scan_id in ids else (ids[-1] if ids else None)
        if sid is None:
            return _error(404, "no_scan", lang, "Fă întâi o verificare a rețelei." if lang == "ro"
                          else "Check your network first.")
        a = get_analysis(conn, sid)
        prev = history.previous_id(conn, sid)
        previous = get_analysis(conn, prev) if prev is not None else None
    turns = [t.model_dump() for t in body.history]
    # "how do I turn it off on my TP-Link?": steps for that maker, looked up on its official site
    from ..ai.guide import device_steps_target
    from ..ai.language import detect as detect_language
    from ..ai.providers import LLMUnavailable
    earlier = next((t["content"] for t in reversed(turns) if t["role"] == "user"), "")
    target = device_steps_target(body.question, a.devices(), a.prioritized(), earlier)
    if target:
        qlang = detect_language(body.question, default=detect_language(earlier, default=lang) if earlier else lang)
        try:
            g = _device_guide(target[0], target[1], qlang)
            return {"answer": g["answer"], "source": "ai", "mode": "guide", "scan_id": sid,
                    "sources": g["sources"], "vendor": g["vendor"]}
        except (ValueError, LLMUnavailable):
            pass                          # no search right now: the normal assistant answers
    ans = ai_ask(body.question, a, lang, previous, history=turns or None, style=body.style)
    mode = "ai" if ans.source == "ai" else ("rejected" if (ans.reason or "").startswith("grounding") else "offline")
    return {"answer": ans.text, "source": ans.source, "mode": mode, "scan_id": sid}


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2400)


@router.post("/tts")
def tts(body: TTSRequest, request: Request):
    """Voice mode: a natural voice for one answer, so every device (computer, phone, tablet) hears the same one.
    1. Piper on this computer (free, private, ai/local_tts.py), 2. the team gateway's voice (OpenAI / ElevenLabs,
    key only there), else 503 tts_unavailable and the page uses the browser's own voice."""
    lang = _lang(request)
    from ..ai import local_tts
    from ..ai.voice import to_speech_text
    text = to_speech_text(body.text, lang, max_sentences=8, max_chars=local_tts.MAX_CHARS) or body.text[:local_tts.MAX_CHARS]
    try:
        return Response(content=local_tts.synthesize(text, lang), media_type="audio/wav", headers={"Cache-Control": "no-store"})
    except local_tts.TTSUnavailable:
        pass
    provider = get_provider()
    speak = getattr(provider, "tts", None)
    if speak is None:
        return _error(503, "tts_unavailable", lang, "voice off")
    try:
        audio = speak(text, lang)
    except LLMUnavailable:
        return _error(503, "tts_unavailable", lang, "voice off")
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


class GuideRequest(BaseModel):
    scan_id: int
    ip: str = Field(max_length=64)
    code: str = Field(max_length=40)


_guides: dict = {}          # (vendor, model, type, code, lang) -> answer; the same device asks once per run


def _device_guide(dev: dict, code: str, lang: str) -> dict:
    """Steps for `code` on `dev`, for its maker (cached). Raises ValueError (unknown maker) or LLMUnavailable."""
    from ..ai.guide import build_guide_request, vendor_name
    from ..ai.providers import LLMUnavailable
    from ..explain.texts import text_for
    req = build_guide_request(dev, code, text_for(code, lang)["steps"], lang)
    key = (req["vendor"], req["model"], req["type"], req["code"], req["lang"])
    if key not in _guides:
        provider = get_provider()
        if not hasattr(provider, "guide"):
            raise LLMUnavailable("AI disabled")
        _guides[key] = provider.guide(req)
    return {**_guides[key], "vendor": vendor_name(req["vendor"]), "model": req["model"]}


@router.post("/guide")
def guide(body: GuideRequest, request: Request):
    """Steps for one problem on one device, for its maker and model, looked up on the maker's official site."""
    from ..ai.providers import LLMUnavailable
    from .app import get_analysis
    lang = _lang(request)
    with history.open_history() as conn:
        try:
            a = get_analysis(conn, body.scan_id)
        except KeyError:
            return _error(404, "no_scan", lang, "Verificarea nu mai există." if lang == "ro" else "This check no longer exists.")
    dev = next((d for d in a.devices() if d["ip"] == body.ip), None)
    if dev is None or not any(f.ip == body.ip and f.code == body.code for f in a.findings):
        return _error(404, "no_problem", lang, "Problema nu mai apare în verificare." if lang == "ro"
                      else "This problem is not in the check.")
    try:
        return _device_guide(dev, body.code, lang)
    except ValueError:
        return _error(422, "unknown_maker", lang, "Nu știm cine a făcut acest aparat, așa că rămân pașii generali." if lang == "ro"
                      else "We do not know who made this device, so the general steps stay.")
    except LLMUnavailable:
        return _error(503, "ai_offline", lang, "Asistentul online nu răspunde acum. Pașii generali de mai sus rămân valabili." if lang == "ro"
                      else "The online assistant is not answering right now. The general steps above still apply.")


# ------------------------------------------------------------------ SafeHouse page data + file upload
@router.get("/ui-data")
def ui_data():
    from .app import ui_data as build
    return build()


@router.post("/upload")
async def upload(request: Request, files: list[UploadFile] = File(...)):
    """Analyse uploaded scan files with the same core as the CLI and save them to the local history.
    A file that cannot be read is kept by name only (no content), so the list and the CSV export show
    it with ERROR - never a crash."""
    from ..core.parser import MAX_FILE_BYTES
    from .app import _remember, analyze_bytes
    lang = _lang(request)
    if len(files) > MAX_EXPORT_FILES:          # never drop files silently: every one must get its row
        return _error(413, "too_many", lang, f"Maximum {MAX_EXPORT_FILES} files.")
    saved, errors = [], []
    with history.open_history() as conn:
        for f in files:
            data = await f.read(MAX_FILE_BYTES + 1)
            name = Path(f.filename or "upload.xml").name[:120]
            a = analyze_bytes(data, name)
            if not a.ok:
                bad_id, _created = history.save_error(conn, name, a.error)
                errors.append({"file": name, "error": a.error, "scan_id": bad_id})
                continue
            scan_id, _created = history.save(conn, a)
            _remember(scan_id, a)
            saved.append(scan_id)
    msg = None
    if errors:
        msg = ("Fișierul nu poate fi citit: e stricat sau nu e o verificare Nmap." if lang == "ro"
               else "The file cannot be read: it is broken or not an Nmap check.")
    return {"saved": saved, "errors": errors, "message": msg}


# ------------------------------------------------------------------ standard results export (FR-15)
MAX_EXPORT_FILES = 500


def exports_dir() -> Path:
    """Where exports are also saved, so they can be found again: ~/SafeHouse/exports (or NETCHECK_EXPORTS)."""
    return Path(os.environ.get("NETCHECK_EXPORTS") or Path.home() / "SafeHouse" / "exports")


def _export_response(results: list, lang: str):
    """findings.csv + scores.csv written by core.analysis.write_results - the very same code as
    `python -m netcheck analyze <folder>` - saved on disk and sent back as one ZIP."""
    import io
    import zipfile
    from datetime import datetime
    from urllib.parse import quote

    from fastapi.responses import Response

    from ..core.analysis import write_results
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = exports_dir() / f"export_{stamp}"
    f_csv, s_csv = write_results(results, out)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(f_csv, "findings.csv")
        z.write(s_csv, "scores.csv")
    bad = sum(1 for r in results if not r.ok)
    return Response(buf.getvalue(), media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="safehouse_results_{stamp}.zip"',
        "X-SafeHouse-Files": str(len(results)),
        "X-SafeHouse-Errors": str(bad),
        "X-SafeHouse-Findings": str(sum(len(r.findings) for r in results)),
        "X-SafeHouse-Saved-To": quote(str(out)),
        "Cache-Control": "no-store",
    })


@router.post("/export")
async def export(request: Request, files: list[UploadFile] = File(...)):
    """One row per finding and one score per file; a file that cannot be read gets ERROR (never a crash).
    Files are sorted by name, like the CLI. Nothing is saved to the history."""
    from ..core.parser import MAX_FILE_BYTES
    from .app import analyze_bytes
    lang = _lang(request)
    if len(files) > MAX_EXPORT_FILES:
        return _error(413, "too_many", lang, f"Maximum {MAX_EXPORT_FILES} files.")
    results = []
    for f in files:
        data = await f.read(MAX_FILE_BYTES + 1)
        results.append(analyze_bytes(data, Path(f.filename or "scan.xml").name[:200]))
    results.sort(key=lambda a: a.file)
    return _export_response(results, lang)


@router.post("/export/history")
def export_history(request: Request):
    from ..core.analysis import Analysis
    from .app import get_analysis
    lang = _lang(request)
    with history.open_history() as conn:
        results = [Analysis(file=e["file"], error=e["error"]) if e["error"] else get_analysis(conn, e["scan_id"])
                   for e in history.entries(conn)]
    results.sort(key=lambda a: a.file)          # by file name, exactly like the CLI and the expected CSVs
    if not results:
        return _error(404, "no_scan", lang, "Nu există verificări salvate." if lang == "ro" else "There are no saved checks.")
    return _export_response(results, lang)


@router.post("/report/{scan_id}")
def technical_report(scan_id: int, request: Request):
    """The technical report of one saved check: a .txt file, also kept next to the CSV exports."""
    import re
    from datetime import datetime
    from urllib.parse import quote

    from fastapi.responses import Response

    from ..explain.technical import technical_report as build
    from .app import get_analysis
    lang = _lang(request)
    with history.open_history() as conn:
        try:
            a = get_analysis(conn, scan_id)
        except KeyError:
            return _error(404, "no_scan", lang, "Verificarea nu există sau fișierul nu a putut fi citit." if lang == "ro"
                          else "This check does not exist or its file could not be read.")
        prev = history.previous_id(conn, scan_id)
        changes = history.changes(conn, prev, scan_id) if prev is not None else None
    text = build(a, lang, changes)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(a.file).stem)[:60] or "scan"
    name = f"safehouse_report_{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    out = exports_dir()
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(text, encoding="utf-8")
    return Response(text.encode("utf-8"), media_type="text/plain; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{name}"',
        "X-SafeHouse-Saved-To": quote(str(out / name)),
        "Cache-Control": "no-store",
    })


class GuardRequest(BaseModel):
    on: bool
    confirm: bool = False


class GuardAck(BaseModel):
    id: str = Field(max_length=20)
    mine: bool


@router.get("/guard")
def guard_status():
    return _guard().status()


@router.post("/guard")
def guard_switch(body: GuardRequest, request: Request):
    """Start / stop guarding the network this computer is on. Same rules as a check: only this network,
    only after the user says it is theirs; no admin rights needed (connect scan only)."""
    lang = _lang(request)
    g = _guard()
    if not body.on:
        g.stop()
        return g.status()
    if not body.confirm:
        return _error(400, "need_consent", lang, "Confirmă întâi că e rețeaua ta." if lang == "ro"
                      else "First confirm that this is your network.")
    net = agent.network_info()
    if not net.get("ok"):
        return _error(403, net.get("code", "refused"), lang,
                      "Această rețea nu poate fi păzită (nu pare o rețea de acasă)." if lang == "ro"
                      else "This network cannot be guarded (it does not look like a home network).")
    try:
        g.start(net["subnet"], net.get("ip"))
    except guardrail.ScopeError:
        return _error(403, "refused", lang, "Această rețea nu poate fi păzită." if lang == "ro" else "This network cannot be guarded.")
    return g.status()


@router.post("/guard/forget")
def guard_forget():
    """„Uită aparatele": the guard learns this network again; saved checks stay."""
    g = _guard()
    g.forget_network()
    return g.status()


class GuardDevice(BaseModel):
    id: str = Field(max_length=40)
    action: str = Field(pattern="^(mine|stranger|forget)$")


@router.post("/guard/device")
def guard_device(body: GuardDevice):
    """One device in the guard's list: "it is mine", "I do not know it" or "forget it"."""
    g = _guard()
    return {"ok": g.device(body.id, body.action), **g.status()}


@router.post("/guard/ack")
def guard_ack(body: GuardAck):
    return {"ok": _guard().ack(body.id, body.mine)}


# ------------------------------------------------------------------ privacy + app lifecycle
@router.delete("/history")
def delete_history():
    from .app import _cache
    history.delete_history()
    _cache.clear()
    _guides.clear()
    _guard().forget()
    return {"deleted": True}


@router.post("/heartbeat")
def heartbeat():
    life.heartbeat()
    return {"ok": True}


@router.post("/shutdown")
def shutdown():
    return {"stopping": life.stop()}
