"""Model backends behind the gateway. Default: Claude API (key only on the gateway machine).

Each backend takes the fixed messages built by prompts.build_messages
([system, user, (assistant, user)...]) and returns plain answer text.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Protocol

from .config import Config

_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)


class BackendError(Exception):
    """The model could not answer (offline, timeout, API error...). Message is safe to log."""


class Backend(Protocol):
    name: str

    def complete(self, messages: list[dict]) -> str: ...

    def health(self) -> dict: ...


def _api_error_detail(e: urllib.error.HTTPError, secrets: tuple[str, ...]) -> str:
    """Short, safe reason from an API error body, e.g. 'invalid_request_error: credit balance is too low'."""
    try:
        err = json.loads(e.read().decode("utf-8", "replace")).get("error") or {}
        detail = f"{err.get('type', '')}: {err.get('message', '')}".strip(": ")
    except Exception:  # noqa: BLE001
        detail = ""
    for s in secrets:
        if s:
            detail = detail.replace(s, "***")
    return detail[:200]


def _post_json(url: str, body: dict, headers: dict, timeout: float, label: str,
               secrets: tuple[str, ...] = (), local: bool = False) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"content-type": "application/json", **headers})
    # a local backend (Ollama) must never go through a system proxy
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if local else urllib.request.build_opener()
    try:
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = _api_error_detail(e, secrets)
        raise BackendError(f"{label} HTTP {e.code}" + (f" ({detail})" if detail else "")) from None
    except urllib.error.URLError as e:
        raise BackendError(f"{label} unreachable: {e.reason.__class__.__name__}: {str(e.reason)[:120]}") from None
    except (TimeoutError, OSError) as e:
        raise BackendError(f"{label} unreachable: {e.__class__.__name__}: {str(e)[:120]}") from None
    except json.JSONDecodeError:
        raise BackendError(f"{label} returned invalid JSON") from None


_SENTENCE_END = re.compile(r"[.!?…](?=\s|$)|\n")


def trim_to_last_sentence(text: str) -> str:
    """A cut-off answer is shown up to its last complete sentence/line, never mid-word."""
    ends = [m.end() for m in _SENTENCE_END.finditer(text)]
    return text[:ends[-1]].strip() if ends else ""


class ClaudeBackend:
    """Claude Messages API on the standard library (no SDK needed)."""

    name = "claude"
    URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, cfg: Config, url: str | None = None):
        if not cfg.anthropic_api_key:
            raise BackendError("ANTHROPIC_API_KEY is not set on the gateway")
        self.cfg = cfg
        self.url = url or self.URL

    def __repr__(self) -> str:  # never print the key
        return f"ClaudeBackend(model={self.cfg.claude_model!r})"

    def complete(self, messages: list[dict]) -> str:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        body = {"model": self.cfg.claude_model, "max_tokens": self.cfg.max_output_tokens,
                "system": system, "messages": convo,
                # Haiku 5.5 has adaptive thinking ON by default and thinking tokens count toward
                # max_tokens: a small limit can end after the thinking block with no text at all.
                "output_config": {"effort": self.cfg.claude_effort}}
        if not self.cfg.claude_thinking:
            body["thinking"] = {"type": "disabled"}
        data = _post_json(
            self.url,
            body,
            {"x-api-key": self.cfg.anthropic_api_key, "anthropic-version": self.API_VERSION},
            self.cfg.model_timeout_s, "claude", secrets=(self.cfg.anthropic_api_key,),
        )
        text = "\n".join(b.get("text", "") for b in data.get("content") or [] if b.get("type") == "text").strip()
        stop = data.get("stop_reason")
        if stop == "max_tokens":
            text = trim_to_last_sentence(text)
        if not text:
            raise BackendError(f"claude returned no text (stop_reason={stop})")
        return text

    def health(self) -> dict:
        # no API call here: health checks must not spend credits
        return {"backend": self.name, "configured": True}


class OllamaBackend:
    """Optional: a local model through Ollama (kept for offline demos)."""

    name = "ollama"

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def complete(self, messages: list[dict]) -> str:
        data = _post_json(
            f"{self.cfg.ollama_url}/api/chat",
            {"model": self.cfg.ollama_model, "messages": messages, "stream": False, "think": False,
             "keep_alive": "30m",
             "options": {"temperature": 0.2, "num_ctx": self.cfg.num_ctx, "num_predict": self.cfg.max_output_tokens}},
            {}, self.cfg.model_timeout_s, "ollama", local=True,
        )
        text = _THINK.sub("", (data.get("message") or {}).get("content") or "").strip()
        if not text:
            raise BackendError("ollama returned an empty answer")
        return text

    def health(self) -> dict:
        try:
            with urllib.request.urlopen(f"{self.cfg.ollama_url}/api/tags", timeout=3) as resp:
                tags = json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - health must never raise
            return {"backend": self.name, "configured": False, "detail": e.__class__.__name__}
        names = {m.get("name") for m in tags.get("models", [])} | {m.get("model") for m in tags.get("models", [])}
        return {"backend": self.name, "configured": self.cfg.ollama_model in names}


def make_backend(cfg: Config) -> Backend:
    if cfg.backend == "claude":
        return ClaudeBackend(cfg)
    if cfg.backend == "ollama":
        return OllamaBackend(cfg)
    raise BackendError(f"unknown backend {cfg.backend!r} (use claude or ollama)")
