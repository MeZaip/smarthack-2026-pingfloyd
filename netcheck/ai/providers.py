"""LLM providers. Configuration only through environment variables (NFR-01).

  NETCHECK_LLM_PROVIDER   claude | none        (default: claude if a key is set, else none)
  ANTHROPIC_API_KEY       your key - never commit it; put it in .env (git-ignored)
  NETCHECK_LLM_MODEL      default: claude-haiku-5-5
  NETCHECK_LLM_TIMEOUT    seconds, default 20
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional, Protocol


class LLMUnavailable(Exception):
    """Any reason we cannot get an answer: no key, offline, timeout, API error."""


class Provider(Protocol):
    name: str

    def create(self, *, system: str, messages: list[dict], tools: list[dict],
               max_tokens: int = 700) -> dict: ...


class NoProvider:
    name = "none"

    def create(self, **_: Any) -> dict:
        raise LLMUnavailable("AI disabled")


class ClaudeProvider:
    """Minimal Messages API client on the standard library (no SDK needed)."""

    name = "claude"
    URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, model: Optional[str] = None, timeout: Optional[float] = None):
        if not api_key:
            raise LLMUnavailable("ANTHROPIC_API_KEY is not set")
        self._key = api_key
        self.model = model or os.environ.get("NETCHECK_LLM_MODEL", "claude-haiku-5-5")
        self.timeout = timeout or float(os.environ.get("NETCHECK_LLM_TIMEOUT", "20"))

    def __repr__(self) -> str:  # never print the key
        return f"ClaudeProvider(model={self.model!r})"

    def create(self, *, system: str, messages: list[dict], tools: list[dict],
               max_tokens: int = 700) -> dict:
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
            "tools": tools,
        }
        req = urllib.request.Request(
            self.URL,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self._key,
                "anthropic-version": self.API_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # do not echo the response body: it could contain request details
            raise LLMUnavailable(f"API error HTTP {e.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise LLMUnavailable(f"network error: {e.__class__.__name__}") from None
        except json.JSONDecodeError:
            raise LLMUnavailable("invalid API response") from None


def load_dotenv(path: str = ".env") -> None:
    """Tiny .env loader (KEY=VALUE lines). Existing env vars win."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


def get_provider() -> Provider:
    load_dotenv()
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    choice = os.environ.get("NETCHECK_LLM_PROVIDER", "claude" if key else "none").lower()
    if choice == "claude" and key:
        return ClaudeProvider(key)
    return NoProvider()
