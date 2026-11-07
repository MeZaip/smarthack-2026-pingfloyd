"""Gateway configuration - environment variables only (NFR-01).

The Anthropic API key lives ONLY here, on the machine that runs the gateway.
It is never sent to, or needed by, the SafeHouse app that users run.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    # network
    host: str = "127.0.0.1"
    port: int = 8787
    token: str = field(default="", repr=False)   # optional bearer token (required when not bound to localhost)
    trust_proxy: bool = False                    # use CF-Connecting-IP / X-Forwarded-For (behind a tunnel)

    # model backend
    backend: str = "claude"                      # claude | ollama
    anthropic_api_key: str = field(default="", repr=False)
    claude_model: str = "claude-haiku-5-5"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:9b"
    model_timeout_s: int = 30
    num_ctx: int = 4096                          # ollama only
    max_output_tokens: int = 1024
    claude_thinking: bool = False                # Haiku 5.5 thinks by default; off = fast, short, predictable
    claude_effort: str = "low"

    # abuse / cost protection
    rate_per_min: int = 12                       # per client IP
    daily_limit: int = 2000                      # total questions per day (protects API credits)
    concurrency: int = 2                         # simultaneous model calls
    queue_wait_s: int = 30
    max_body: int = 256 * 1024

    @property
    def model(self) -> str:
        return self.claude_model if self.backend == "claude" else self.ollama_model

    @staticmethod
    def from_env() -> "Config":
        backend = os.environ.get("NETCHECK_GATEWAY_BACKEND", "claude").lower()
        return Config(
            host=os.environ.get("NETCHECK_GATEWAY_HOST", "127.0.0.1"),
            port=_int("NETCHECK_GATEWAY_PORT", 8787),
            token=os.environ.get("NETCHECK_GATEWAY_TOKEN", ""),
            trust_proxy=os.environ.get("NETCHECK_GATEWAY_TRUST_PROXY", "") == "1",
            backend=backend,
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            claude_model=os.environ.get("NETCHECK_GATEWAY_CLAUDE_MODEL", "claude-haiku-5-5"),
            ollama_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
            ollama_model=os.environ.get("NETCHECK_GATEWAY_OLLAMA_MODEL", "qwen3.5:9b"),
            model_timeout_s=_int("NETCHECK_GATEWAY_MODEL_TIMEOUT", 30 if backend == "claude" else 90),
            num_ctx=_int("NETCHECK_GATEWAY_NUM_CTX", 4096),
            max_output_tokens=_int("NETCHECK_GATEWAY_MAX_OUTPUT_TOKENS", 1024),
            claude_thinking=os.environ.get("NETCHECK_GATEWAY_CLAUDE_THINKING", "") == "1",
            claude_effort=os.environ.get("NETCHECK_GATEWAY_CLAUDE_EFFORT", "low"),
            rate_per_min=_int("NETCHECK_GATEWAY_RATE_PER_MIN", 12),
            daily_limit=_int("NETCHECK_GATEWAY_DAILY_LIMIT", 2000),
            concurrency=max(1, _int("NETCHECK_GATEWAY_CONCURRENCY", 2 if backend == "claude" else 1)),
            queue_wait_s=_int("NETCHECK_GATEWAY_QUEUE_WAIT", 30),
            max_body=_int("NETCHECK_GATEWAY_MAX_BODY", 256 * 1024),
        )

    def describe(self) -> str:
        return (f"listening on http://{self.host}:{self.port}  backend={self.backend}  model={self.model}  "
                f"auth={'on' if self.token else 'off'}  rate={self.rate_per_min}/min/IP  "
                f"daily_limit={self.daily_limit}  concurrency={self.concurrency}")

    def ready(self) -> bool:
        """Can this machine run the gateway? (claude: a key is set here; ollama: always try)."""
        return self.backend == "ollama" or (self.backend == "claude" and bool(self.anthropic_api_key))
