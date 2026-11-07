"""Client for the team-hosted AI gateway. End users configure nothing.

  NETCHECK_AI_URL      gateway base URL (default http://127.0.0.1:8787)
  NETCHECK_AI_TOKEN    optional bearer token, only if the gateway requires one
  NETCHECK_AI_TIMEOUT  seconds, default 30
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from ..core.analysis import Analysis
from .contract import build_request
from .providers import LLMUnavailable

DEFAULT_URL = "http://127.0.0.1:8787"


def _reason(err) -> str:
    """Short, user-safe reason (no request data, no headers)."""
    if isinstance(err, (TimeoutError,)) or "timed out" in str(err):
        return "timed out"
    if isinstance(err, OSError) and err.errno is not None:
        return f"{err.__class__.__name__} [errno {err.errno}] {err.strerror or ''}".strip()
    return f"{err.__class__.__name__}: {str(err)[:120]}"


class RemoteProvider:
    kind = "remote"
    name = "gateway"

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None, timeout: Optional[float] = None):
        self.url = (url or os.environ.get("NETCHECK_AI_URL") or DEFAULT_URL).rstrip("/")
        u = urllib.parse.urlsplit(self.url)
        if not (u.scheme == "https" or (u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost", "::1"))):
            # anything leaving this machine must be encrypted
            raise LLMUnavailable("NETCHECK_AI_URL must be https:// (or a localhost address)")
        self._token = token if token is not None else os.environ.get("NETCHECK_AI_TOKEN", "")
        self.timeout = timeout or float(os.environ.get("NETCHECK_AI_TIMEOUT", "30"))
        # A local gateway must never go through a system/corporate proxy (Windows urllib reads
        # the IE/registry proxy and, unlike browsers, does not bypass 127.0.0.1 by default).
        handlers = [urllib.request.ProxyHandler({})] if u.hostname in ("127.0.0.1", "localhost", "::1") else []
        self._opener = urllib.request.build_opener(*handlers)

    def __repr__(self) -> str:
        return f"RemoteProvider(url={self.url!r})"

    def _request(self, method: str, path: str, payload: Optional[dict] = None, timeout: Optional[float] = None) -> dict:
        headers = {"accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["content-type"] = "application/json"
        if self._token:
            headers["authorization"] = f"Bearer {self._token}"
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers)
        try:
            with self._opener.open(req, timeout=timeout or self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            code, message = "error", ""
            try:
                body = json.loads(e.read().decode("utf-8"))
                code, message = body.get("error", code), str(body.get("message", ""))[:240]
            except Exception:  # noqa: BLE001
                pass
            raise LLMUnavailable(f"gateway HTTP {e.code} ({code})" + (f": {message}" if message else "")) from None
        except urllib.error.URLError as e:
            raise LLMUnavailable(f"gateway unreachable at {self.url}: {_reason(e.reason)}") from None
        except (TimeoutError, OSError) as e:
            raise LLMUnavailable(f"gateway unreachable at {self.url}: {_reason(e)}") from None
        except json.JSONDecodeError:
            raise LLMUnavailable("gateway returned invalid JSON") from None

    def answer(self, question: str, analysis: Analysis, lang: str = "ro",
               previous: Optional[Analysis] = None, history: Optional[list[dict]] = None) -> str:
        resp = self._request("POST", "/v1/ask", build_request(question, analysis, lang, previous, history))
        text = resp.get("answer")
        if not isinstance(text, str) or not text.strip():
            raise LLMUnavailable("gateway returned no answer")
        return text.strip()[:4000]

    def status(self) -> dict:
        """For the UI badge: is the assistant online right now?"""
        try:
            h = self._request("GET", "/health", timeout=3)
            return {"online": bool(h.get("ok")), "model": h.get("model")}
        except LLMUnavailable as e:
            return {"online": False, "reason": str(e)}
