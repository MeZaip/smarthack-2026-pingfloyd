"""Protects the local agent from other websites open in the same browser.

A web page on any site could otherwise send requests to http://127.0.0.1:<port> and start a scan
or delete the history (CSRF), or reach it through a hostile DNS name (DNS rebinding). So:

1. Host check: only requests addressed to this computer (127.0.0.1 / localhost) are answered.
2. Session cookie: every page we serve sets a random, per-run cookie with SameSite=Strict. Browsers
   never attach it to requests started by another site, and every state-changing request
   (POST/PUT/PATCH/DELETE) must carry it.
3. Origin check: if the browser says where a state-changing request comes from, it must be us.

No login is needed: the agent only listens on this computer and only the page it served can act.
"""
from __future__ import annotations

import hmac
import os
import secrets
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

COOKIE = "nc_session"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "testserver"}   # testserver = FastAPI TestClient
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}

SESSION_TOKEN = os.environ.get("NETCHECK_SESSION_TOKEN") or secrets.token_urlsafe(32)


def _hostname(value: str) -> str:
    if not value:
        return ""
    try:
        return (urlsplit(value if "//" in value else f"//{value}").hostname or "").lower()
    except ValueError:
        return ""


def host_allowed(host_header: str) -> bool:
    if os.environ.get("NETCHECK_ALLOW_ANY_HOST") == "1":   # `netcheck serve --host <ip>`, opted in explicitly
        return True
    return _hostname(host_header) in LOCAL_HOSTS


class LocalOnly(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not host_allowed(request.headers.get("host", "")):
            return JSONResponse({"error": {"code": "forbidden_host", "message": "local access only"}}, 403)
        if request.method in UNSAFE:
            got = request.cookies.get(COOKIE, "")
            if not hmac.compare_digest(got.encode(), SESSION_TOKEN.encode()):
                return JSONResponse({"error": {"code": "session", "message":
                                     "Reîncarcă pagina și încearcă din nou. / Reload the page and try again."}}, 403)
            origin = request.headers.get("origin")
            if origin and not host_allowed(origin):
                return JSONResponse({"error": {"code": "forbidden_origin", "message": "cross-site request"}}, 403)
        response = await call_next(request)
        if request.method == "GET":
            response.set_cookie(COOKIE, SESSION_TOKEN, httponly=True, samesite="strict", path="/")
        return response
