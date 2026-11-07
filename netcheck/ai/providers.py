"""Which assistant the app uses. The app NEVER holds an API key.

  NETCHECK_LLM_PROVIDER   gateway | none     (default: gateway)
      gateway -> the team's AI gateway (netcheck/ai/remote.py); the gateway holds the key
      none    -> built-in texts only
"""
from __future__ import annotations

import os


class LLMUnavailable(Exception):
    """Any reason we cannot get an AI answer: offline, timeout, gateway error..."""


class NoProvider:
    kind = "none"
    name = "none"

    def answer(self, *_, **__) -> str:
        raise LLMUnavailable("AI disabled")

    def status(self) -> dict:
        return {"online": False, "reason": "AI disabled"}


_PROJECT_ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")


def load_dotenv(path: str | None = None) -> None:
    """Tiny .env loader (KEY=VALUE lines). Existing env vars win; empty values are ignored.
    Looks in the current directory first, then in the project root."""
    if path is None:
        for candidate in (".env", _PROJECT_ENV):
            load_dotenv(candidate)
        return
    try:
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v:  # empty values keep the built-in defaults
                    os.environ.setdefault(k.strip(), v)
    except OSError:
        pass


def get_provider():
    load_dotenv()
    if os.environ.get("NETCHECK_LLM_PROVIDER", "gateway").lower() == "none":
        return NoProvider()
    from .remote import RemoteProvider
    try:
        return RemoteProvider()
    except LLMUnavailable:
        return NoProvider()
