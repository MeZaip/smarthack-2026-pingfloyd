"""HTTP server for the AI gateway (standard library only - no extra dependencies).

The SafeHouse app (run by end users) calls this service; the service calls the
model with the team's API key. Users never see or need a key.

Endpoints
  GET  /health    -> {"ok": bool, "backend": str, "model": str}
  POST /v1/ask    -> {"answer": str, "model": str, "ms": int}
  POST /v1/guide  -> {"answer": str, "sources": [{"title", "url"}], "model": str, "ms": int}
                     fix steps for one device brand/model, searched only on the maker's official site

Protections: optional bearer token, per-IP rate limit, daily cap (protects API
credits), body size limit, strict request whitelist (netcheck.ai.contract),
bounded concurrency, grounding check with one retry, no logging of request
content or client IPs.
"""
from __future__ import annotations

import datetime as _dt
import hmac
import json
import re
import sys
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from netcheck.ai.contract import ContractError, evidence_from_context, validate_request
from netcheck.ai.grounding import GroundingError, check_evidence

from .backends import Backend, BackendError, make_backend
from .config import Config
from netcheck.ai.guide import domains, validate_guide_request, vendor_name
from netcheck.explain.texts import text_for

from .prompts import GUIDE_RETRY, RETRY_NOTE, build_guide, build_messages


class RateLimiter:
    """Sliding window: at most `per_min` requests per key in the last 60 s."""

    def __init__(self, per_min: int):
        self.per_min = per_min
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self.per_min <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_min:
                return False
            q.append(now)
            if len(self._hits) > 10000:  # bounded memory
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return True


class DailyBudget:
    """Global cap on model calls per (UTC) day - a hard ceiling on API spend."""

    def __init__(self, limit: int):
        self.limit = limit
        self._day = None
        self._used = 0
        self._lock = threading.Lock()

    def take(self) -> bool:
        if self.limit <= 0:
            return True
        today = _dt.datetime.now(_dt.timezone.utc).date()
        with self._lock:
            if today != self._day:
                self._day, self._used = today, 0
            if self._used >= self.limit:
                return False
            self._used += 1
            return True


_BOLD = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.S)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.M)


def plain_text(text: str) -> str:
    """Safety net for the 'no Markdown' prompt rule: the app shows answers as plain text."""
    text = _BOLD.sub(lambda m: m.group(1) or m.group(2), text)
    return _HEADING.sub("", text).strip()


MAX_WORDS = 110          # the prompt asks for ~60 words (+ up to 3 short steps); this is only the safety net
_SENTENCE = re.compile(r"(?<=[.!?…])\s+")
_STEP = re.compile(r"^\s*\d+[.)]\s")


def shorten(text: str, max_words: int = MAX_WORDS) -> str:
    """Safety net for the 'be short' prompt rule: keep whole sentences / numbered steps up to max_words."""
    if len(text.split()) <= max_words:
        return text
    out, used = [], 0
    for line in text.splitlines():
        parts = [line] if _STEP.match(line) else _SENTENCE.split(line)
        kept, full = [], False
        for part in parts:
            words = len(part.split())
            if used + words > max_words:
                full = True
                break
            kept.append(part)
            used += words
        if kept:
            out.append(" ".join(kept))
        if full:
            break
    short = "\n".join(x for x in out if x.strip()).strip()
    return short or text


class GatewayError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def answer_question(cfg: Config, backend: Backend, slots: threading.BoundedSemaphore,
                    budget: DailyBudget, body: dict) -> tuple[str, int]:
    """Core logic, independent of HTTP. Returns (answer, elapsed_ms)."""
    try:
        lang, question, ctx, history = validate_request(body)
    except ContractError as e:
        raise GatewayError(400, "bad_request", str(e)) from None
    evidence = evidence_from_context(ctx)
    messages = build_messages(lang, question, ctx, history)

    if not budget.take():
        raise GatewayError(503, "daily_limit", "the assistant reached today's limit, built-in answers still work")
    if not slots.acquire(timeout=cfg.queue_wait_s):
        raise GatewayError(503, "busy", "the assistant is busy, try again in a moment")
    started = time.monotonic()
    try:
        for attempt in range(2):
            try:
                text = backend.complete(messages)
            except BackendError as e:
                raise GatewayError(503, "model_unavailable", str(e)) from None
            text = shorten(plain_text(text))
            try:
                check_evidence(text, *evidence)
                return text, int((time.monotonic() - started) * 1000)
            except GroundingError as e:
                if attempt == 1:
                    raise GatewayError(502, "ungrounded", "the model answer could not be verified") from None
                messages = messages + [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": RETRY_NOTE[lang].format(reason=str(e))},
                ]
    finally:
        slots.release()
    raise GatewayError(502, "ungrounded", "the model answer could not be verified")  # pragma: no cover


GUIDE_MAX_WORDS = 170


def guide_answer(cfg: Config, backend: Backend, slots: threading.BoundedSemaphore,
                 budget: DailyBudget, body: dict) -> tuple[str, list[dict], int]:
    """Steps for one device brand/model (web search limited to the maker's site). Returns (answer, sources, ms)."""
    try:
        req = validate_guide_request(body)
    except ContractError as e:
        raise GatewayError(400, "bad_request", str(e)) from None
    if not hasattr(backend, "guide"):
        raise GatewayError(501, "not_supported", "this model cannot search the maker's site")
    tx = text_for(req["code"], req["lang"])
    system, user = build_guide(req, tx["title"], tx["explain"], vendor_name(req["vendor"]))
    if not budget.take():
        raise GatewayError(503, "daily_limit", "the assistant reached today's limit, built-in answers still work")
    if not slots.acquire(timeout=cfg.queue_wait_s):
        raise GatewayError(503, "busy", "the assistant is busy, try again in a moment")
    started = time.monotonic()
    try:
        for attempt in range(2):
            try:
                text, sources = backend.guide(system, user, domains(req["vendor"]))
            except BackendError as e:
                raise GatewayError(503, "model_unavailable", str(e)) from None
            text = shorten(plain_text(text), GUIDE_MAX_WORDS)
            try:   # NFR-06: no IPs, ports, CVEs, phone numbers or links in the steps (the scan gave none here)
                check_evidence(text, set(), set(), "")
                break
            except GroundingError as e:
                if attempt == 1:
                    raise GatewayError(502, "ungrounded", "the model answer could not be verified") from None
                user = user + GUIDE_RETRY[req["lang"]].format(reason=str(e))
    finally:
        slots.release()
    allowed = tuple(domains(req["vendor"]))
    sources = [s for s in sources if any((urllib_host(s["url"]) == d or urllib_host(s["url"]).endswith("." + d)) for d in allowed)]
    return text, sources, int((time.monotonic() - started) * 1000)


def urllib_host(url: str) -> str:
    from urllib.parse import urlsplit
    return (urlsplit(url).hostname or "").lower()


def make_handler(cfg: Config, backend: Backend):
    limiter = RateLimiter(cfg.rate_per_min)
    budget = DailyBudget(cfg.daily_limit)
    slots = threading.BoundedSemaphore(cfg.concurrency)

    class Handler(BaseHTTPRequestHandler):
        server_version = "safehouse-gateway"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        # ---------------------------------------------------------- helpers
        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def _client_ip(self) -> str:
            if cfg.trust_proxy:
                fwd = self.headers.get("CF-Connecting-IP") or (self.headers.get("X-Forwarded-For") or "").split(",")[0]
                if fwd.strip():
                    return fwd.strip()
            return self.client_address[0]

        def _authorized(self) -> bool:
            if not cfg.token:
                return True
            got = self.headers.get("Authorization", "")
            return hmac.compare_digest(got.encode(), f"Bearer {cfg.token}".encode())

        def log_message(self, fmt, *args):  # never log bodies or client IPs (privacy)
            pass

        def _log(self, status: int, started: float) -> None:
            sys.stderr.write(f"{time.strftime('%H:%M:%S')} {self.command} {self.path} {status} "
                             f"{int((time.monotonic() - started) * 1000)}ms\n")

        # ---------------------------------------------------------- routes
        def do_GET(self):
            started = time.monotonic()
            if self.path != "/health":
                self._send(404, {"error": "not_found", "message": "not found"})
                return self._log(404, started)
            h = backend.health()
            self._send(200, {"ok": bool(h.get("configured")), "model": cfg.model, **h})
            self._log(200, started)

        def do_POST(self):
            started = time.monotonic()
            status = 500
            try:
                if self.path not in ("/v1/ask", "/v1/guide"):
                    raise GatewayError(404, "not_found", "not found")
                if not self._authorized():
                    raise GatewayError(401, "unauthorized", "missing or wrong token")
                if not limiter.allow(self._client_ip()):
                    raise GatewayError(429, "rate_limited", "too many questions, wait a minute")
                ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                if ctype != "application/json":
                    raise GatewayError(415, "unsupported_media_type", "use application/json")
                try:
                    length = int(self.headers.get("Content-Length", ""))
                except ValueError:
                    raise GatewayError(411, "length_required", "Content-Length required") from None
                if length <= 0 or length > cfg.max_body:
                    raise GatewayError(413, "too_large", f"body must be 1..{cfg.max_body} bytes")
                try:
                    body = json.loads(self.rfile.read(length).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise GatewayError(400, "bad_json", "body is not valid JSON") from None
                if self.path == "/v1/guide":
                    text, sources, ms = guide_answer(cfg, backend, slots, budget, body)
                    status = 200
                    self._send(200, {"answer": text, "sources": sources, "model": cfg.model, "ms": ms})
                else:
                    text, ms = answer_question(cfg, backend, slots, budget, body)
                    status = 200
                    self._send(200, {"answer": text, "model": cfg.model, "ms": ms})
            except GatewayError as e:
                status = e.status
                if e.code == "model_unavailable":   # operator needs the reason; it never contains the key
                    sys.stderr.write(f"{time.strftime('%H:%M:%S')} model error: {e.message}\n")
                self.close_connection = True   # body may be unread; don't reuse the connection
                self._send(e.status, {"error": e.code, "message": e.message})
            except Exception:  # noqa: BLE001 - never leak internals
                status = 500
                self.close_connection = True
                self._send(500, {"error": "internal", "message": "internal error"})
            finally:
                self._log(status, started)

        def do_PUT(self):
            self.close_connection = True
            self._send(405, {"error": "method_not_allowed", "message": "method not allowed"})

        do_DELETE = do_PATCH = do_PUT

    return Handler


def make_server(cfg: Config, backend: Optional[Backend] = None) -> ThreadingHTTPServer:
    if cfg.host not in ("127.0.0.1", "localhost", "::1") and not cfg.token:
        raise SystemExit("Refusing to listen on a non-local address without NETCHECK_GATEWAY_TOKEN. "
                         "Expose the gateway through a tunnel, or set a token.")
    try:
        backend = backend or make_backend(cfg)
    except BackendError as e:
        raise SystemExit(f"Cannot start the gateway: {e}") from None
    try:
        srv = ThreadingHTTPServer((cfg.host, cfg.port), make_handler(cfg, backend))
    except OSError as e:
        raise SystemExit(f"Cannot start the gateway on {cfg.host}:{cfg.port}: {e.strerror or e} "
                         "(another program, or another gateway, already uses this port?)") from None
    srv.daemon_threads = True
    return srv


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    from netcheck.ai.providers import load_dotenv

    load_dotenv()
    p = argparse.ArgumentParser(prog="python -m gateway", description="SafeHouse AI gateway")
    p.add_argument("--host")
    p.add_argument("--port", type=int)
    p.add_argument("--backend", choices=["claude", "ollama"])
    a = p.parse_args(argv)
    cfg = Config.from_env()
    overrides = {k: v for k, v in {"host": a.host, "port": a.port, "backend": a.backend}.items() if v}
    if overrides:
        cfg = Config(**{**cfg.__dict__, **overrides})
    srv = make_server(cfg)
    print(f"SafeHouse gateway {cfg.describe()}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0
