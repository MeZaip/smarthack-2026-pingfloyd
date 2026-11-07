"""/api/v1: the actions the page can ask the local agent to do. The page is a thin client.

  GET    /api/v1/status              network we are on, Nmap installed?, AI online?, scan running?
  POST   /api/v1/scan                {"confirm": true} -> start a check of THIS network (202 + job)
  GET    /api/v1/scan/{job_id}       progress / result of a check
  POST   /api/v1/verify              {"scan_id", "ip", "port", "code"} -> re-check one fixed problem
  POST   /api/v1/ask                 {"question", "scan_id"?, "history"?} -> assistant answer (AI or built-in)
  DELETE /api/v1/history             delete my history (one click, NFR-02)
  POST   /api/v1/heartbeat           the open page is alive (app mode)
  POST   /api/v1/shutdown            "Close NetCheck" (app mode)

Errors: {"error": {"code": "...", "message": "<plain words in the user's language>"}}.
All state-changing calls are protected by web/security.py (local host + session cookie + origin).
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .. import history
from ..ai.assistant import ask as ai_ask
from ..ai.providers import get_provider
from ..net import elevate, guardrail, netdetect, scanner
from ..net import verify as verify_mod
from . import agent

router = APIRouter(prefix="/api/v1", tags=["agent"])

jobs = agent.ScanJobs()
life = agent.AppLife()


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


VERIFY_RESCAN = ("Pentru această problemă e nevoie de o verificare completă: apasă „Verifică rețeaua din nou”.",
                 "This problem needs a full check: press \"Check my network again\".")


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
    ans = ai_ask(body.question, a, lang, previous, history=turns or None)
    mode = "ai" if ans.source == "ai" else ("rejected" if (ans.reason or "").startswith("grounding") else "offline")
    return {"answer": ans.text, "source": ans.source, "mode": mode, "scan_id": sid}


# ------------------------------------------------------------------ privacy + app lifecycle
@router.delete("/history")
def delete_history():
    from .app import _cache
    history.delete_history()
    _cache.clear()
    return {"deleted": True}


@router.post("/heartbeat")
def heartbeat():
    life.heartbeat()
    return {"ok": True}


@router.post("/shutdown")
def shutdown():
    return {"stopping": life.stop()}
