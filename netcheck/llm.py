"""LLM providers for the assistant.

  NETCHECK_LLM=ollama     (default) free local model via Ollama — scan data never leaves the laptop
  NETCHECK_LLM=anthropic  Claude API (needs ANTHROPIC_API_KEY or `ant auth login`)
  NETCHECK_LLM=off        built-in offline answers only

If the chosen provider is not reachable, select_provider() returns None and the assistant
falls back to the offline answerer. Providers only run the tool loop; they never compute findings.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable

Execute = Callable[[str, dict], dict]
Transport = Callable[[str, str, dict | None, float], dict]   # (method, url, json_body, timeout) -> json


class LLMHTTPError(Exception):
    pass


def http_json(method: str, url: str, body: dict | None = None, timeout: float = 180) -> dict:
    """Tiny stdlib JSON client (no extra dependency). Only talks to the local Ollama URL."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LLMHTTPError(str(e)) from None
MAX_TOOL_ROUNDS = 6

OLLAMA_URL = os.environ.get("NETCHECK_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("NETCHECK_OLLAMA_MODEL", "qwen2.5:7b")
ANTHROPIC_MODEL = os.environ.get("NETCHECK_MODEL", "claude-opus-5-5")


class OllamaProvider:
    def __init__(self, model: str = OLLAMA_MODEL, url: str = OLLAMA_URL, transport: Transport | None = None):
        self.model, self.url = model, url.rstrip("/")
        self.transport = transport or http_json
        self.messages: list[dict] = []
        self.label = f"local {model}"
        self.local = True

    @staticmethod
    def _tools(tools: list[dict]) -> list[dict]:
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                  "parameters": t["input_schema"]}} for t in tools]

    def run(self, system: str, tools: list[dict], question: str, execute: Execute) -> tuple[str, list[str]]:
        start = len(self.messages)
        self.messages.append({"role": "user", "content": question})
        evidence: list[str] = []
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                data = self.transport("POST", f"{self.url}/api/chat", {
                    "model": self.model, "stream": False, "options": {"temperature": 0},
                    "messages": [{"role": "system", "content": system}] + self.messages,
                    "tools": self._tools(tools),
                }, 180)
                msg = data.get("message") or {}
                calls = msg.get("tool_calls") or []
                self.messages.append({"role": "assistant", "content": msg.get("content", ""),
                                      **({"tool_calls": calls} if calls else {})})
                if not calls:
                    return (msg.get("content") or "").strip(), evidence
                for c in calls:
                    fn = c.get("function") or {}
                    args = fn.get("arguments") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    out = json.dumps(execute(str(fn.get("name", "")), args if isinstance(args, dict) else {}),
                                     ensure_ascii=False)
                    evidence.append(out)
                    self.messages.append({"role": "tool", "content": out, "tool_name": fn.get("name", "")})
            raise RuntimeError("too many tool rounds")
        except Exception:
            del self.messages[start:]
            raise


class AnthropicProvider:
    def __init__(self, client, model: str = ANTHROPIC_MODEL):
        self.client, self.model = client, model
        self.messages: list = []
        self.label = f"Claude {model}"
        self.local = False

    def run(self, system: str, tools: list[dict], question: str, execute: Execute) -> tuple[str, list[str]]:
        start = len(self.messages)
        self.messages.append({"role": "user", "content": question})
        evidence: list[str] = []
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                resp = self.client.beta.messages.create(
                    model=self.model, max_tokens=4000, system=system, tools=tools, messages=self.messages,
                    output_config={"effort": "low"},
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                )
                if resp.stop_reason == "refusal":
                    raise RuntimeError("model refused")
                self.messages.append({"role": "assistant", "content": resp.content})
                if resp.stop_reason == "pause_turn":
                    continue
                uses = [b for b in resp.content if b.type == "tool_use"]
                if resp.stop_reason != "tool_use" or not uses:
                    return "\n".join(b.text for b in resp.content if b.type == "text").strip(), evidence
                results = []
                for b in uses:
                    out = json.dumps(execute(b.name, b.input if isinstance(b.input, dict) else {}), ensure_ascii=False)
                    evidence.append(out)
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
                self.messages.append({"role": "user", "content": results})
            raise RuntimeError("too many tool rounds")
        except Exception:
            del self.messages[start:]
            raise


def ollama_models(url: str = OLLAMA_URL) -> list[str] | None:
    """Installed model names, or None if Ollama is not running."""
    try:
        data = http_json("GET", f"{url.rstrip('/')}/api/tags", None, 1.5)
        return [m.get("name", "") for m in data.get("models", [])]
    except LLMHTTPError:
        return None


def _has_model(installed: list[str], model: str) -> bool:
    want = model if ":" in model else f"{model}:latest"
    return any(m == model or m == want for m in installed)


def select_provider() -> tuple[object | None, str]:
    choice = os.environ.get("NETCHECK_LLM", "").strip().lower()
    if os.environ.get("NETCHECK_OFFLINE") == "1" or choice == "off":
        return None, "AI turned off"
    if choice in ("", "ollama"):
        installed = ollama_models()
        if installed is not None and _has_model(installed, OLLAMA_MODEL):
            return OllamaProvider(), f"local model {OLLAMA_MODEL} (data stays on this laptop)"
        reason = ("Ollama is not running (start it: ollama serve)" if installed is None
                  else f"model {OLLAMA_MODEL} not downloaded (run: ollama pull {OLLAMA_MODEL})")
        if choice == "ollama" or not os.environ.get("ANTHROPIC_API_KEY"):
            return None, reason
    try:
        import anthropic
        return AnthropicProvider(anthropic.Anthropic(max_retries=1, timeout=60)), f"Claude {ANTHROPIC_MODEL}"
    except Exception as e:
        return None, f"Claude unavailable ({type(e).__name__})"


def status_report() -> str:
    installed = ollama_models()
    lines = [f"NETCHECK_LLM = {os.environ.get('NETCHECK_LLM') or 'ollama (default)'}",
             f"Ollama at {OLLAMA_URL}: " + ("NOT running" if installed is None else "running"),
             f"Wanted model: {OLLAMA_MODEL} — " + ("installed ✔" if installed and _has_model(installed, OLLAMA_MODEL)
                                                  else "missing ✖")]
    if installed:
        lines.append("Installed models: " + ", ".join(installed))
    prov, msg = select_provider()
    lines.append(f"Active: {msg}" if prov else f"Active: offline built-in answers ({msg})")
    if installed is None or not (installed and _has_model(installed, OLLAMA_MODEL)):
        lines += ["", "Setup (do it at home, ~2–5 GB download):",
                  "  brew install ollama        # or download from ollama.com",
                  "  ollama serve               # leave running (the macOS app starts it automatically)",
                  f"  ollama pull {OLLAMA_MODEL}   # smaller laptops: ollama pull qwen2.5:3b + NETCHECK_OLLAMA_MODEL=qwen2.5:3b"]
    return "\n".join(lines)
