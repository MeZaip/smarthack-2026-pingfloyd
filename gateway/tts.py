"""Optional natural voice for the assistant's voice mode (text -> MP3), behind the gateway.

The key lives only on the gateway machine (like ANTHROPIC_API_KEY). The app never sees it and, when no
provider is configured (or it fails), the app uses the browser's own voice instead.

  NETCHECK_GATEWAY_TTS=none|openai|elevenlabs     (default none)
  OPENAI_API_KEY / ELEVENLABS_API_KEY             (only the one you use)

Only the short, already-grounded answer is sent, and only after netcheck.ai.voice.to_speech_text has
removed IP addresses, MAC addresses, port numbers and codes (privacy + it sounds better).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from .config import Config

MAX_AUDIO_BYTES = 4 * 1024 * 1024

# how the voice should sound (OpenAI gpt-4o-mini-tts follows these instructions)
STYLE = {
    "ro": "Vorbește în limba română, cald, calm și prietenos, ca un nepot care își ajută bunicii. Ritm puțin mai lent, clar.",
    "en": "Speak English warmly, calmly and kindly, like a grandchild helping their grandparents. A slightly slower, clear pace.",
}


class TTSError(Exception):
    """The voice could not be made (not configured, API error, timeout). Message is safe to log."""


def _post_audio(url: str, body: dict, headers: dict, timeout: float, label: str, secret: str) -> bytes:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"content-type": "application/json", "accept": "audio/mpeg", **headers})
    try:
        with urllib.request.build_opener().open(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            data = resp.read(MAX_AUDIO_BYTES + 1)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read(400).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            pass
        detail = detail.replace(secret, "***") if secret else detail
        raise TTSError(f"{label} HTTP {e.code}" + (f" ({detail[:160]})" if detail else "")) from None
    except urllib.error.URLError as e:
        raise TTSError(f"{label} unreachable: {e.reason.__class__.__name__}") from None
    except (TimeoutError, OSError) as e:
        raise TTSError(f"{label} unreachable: {e.__class__.__name__}") from None
    if not ctype.startswith("audio/") or not data or len(data) > MAX_AUDIO_BYTES:
        raise TTSError(f"{label} returned no usable audio")
    return data


class OpenAITTS:
    name = "openai"
    URL = "https://api.openai.com/v1/audio/speech"

    def __init__(self, cfg: Config):
        if not cfg.openai_api_key:
            raise TTSError("OPENAI_API_KEY is not set on the gateway")
        self.cfg = cfg

    def __repr__(self) -> str:  # never print the key
        return f"OpenAITTS(model={self.cfg.openai_tts_model!r}, voice={self.cfg.openai_tts_voice!r})"

    def speak(self, text: str, lang: str) -> bytes:
        body = {"model": self.cfg.openai_tts_model, "voice": self.cfg.openai_tts_voice, "input": text,
                "response_format": "mp3"}
        if not self.cfg.openai_tts_model.startswith("tts-1"):     # tts-1 / tts-1-hd take no instructions
            body["instructions"] = STYLE.get(lang, STYLE["en"])
        return _post_audio(self.URL, body, {"authorization": f"Bearer {self.cfg.openai_api_key}"},
                           self.cfg.tts_timeout_s, "openai-tts", self.cfg.openai_api_key)


class ElevenLabsTTS:
    name = "elevenlabs"
    URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"

    def __init__(self, cfg: Config):
        if not cfg.elevenlabs_api_key:
            raise TTSError("ELEVENLABS_API_KEY is not set on the gateway")
        self.cfg = cfg

    def __repr__(self) -> str:
        return f"ElevenLabsTTS(model={self.cfg.elevenlabs_model!r})"

    def speak(self, text: str, lang: str) -> bytes:
        url = self.URL.format(voice=urllib.parse.quote(self.cfg.elevenlabs_voice, safe=""))
        body = {"text": text, "model_id": self.cfg.elevenlabs_model,
                "voice_settings": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.2}}
        return _post_audio(url, body, {"xi-api-key": self.cfg.elevenlabs_api_key},
                           self.cfg.tts_timeout_s, "elevenlabs", self.cfg.elevenlabs_api_key)


def make_tts(cfg: Config) -> Optional[object]:
    """The configured voice, or None (the app then uses the browser voice). Never raises."""
    try:
        if cfg.tts == "openai":
            return OpenAITTS(cfg)
        if cfg.tts == "elevenlabs":
            return ElevenLabsTTS(cfg)
    except TTSError:
        return None
    return None
