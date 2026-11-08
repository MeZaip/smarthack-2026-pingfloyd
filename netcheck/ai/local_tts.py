"""Natural voice made on this computer (voice mode of the assistant), free and private: Piper neural TTS.

No API key, no internet: the short answer is turned into speech here and sent to whatever device opened the
app (computer, phone, tablet), so every device hears the same natural voice, whatever voices it has installed.

Optional. Needs `pip install piper-tts` and the two voice models in voices/piper/ (git-ignored, ~60 MB each):
    python tools/get_voices.py
Voices: Romanian "Mihai" (ro_RO-mihai-medium), English "Lessac" (en_US-lessac-medium), both open (rhasspy/piper-voices).

  NETCHECK_TTS_DIR     where the .onnx voice files are (default: <project>/voices/piper)
  NETCHECK_TTS_SLOW    speaking pace, > 1 is slower (default 1.2: calm, clear, for older listeners)
  NETCHECK_TTS         local (default) | off
"""
from __future__ import annotations

import io
import os
import threading
import wave
from pathlib import Path
from typing import Optional

VOICES = {"ro": "ro_RO-mihai-medium", "en": "en_US-lessac-medium"}
_ROOT = Path(__file__).resolve().parents[2]
MAX_CHARS = 1200


class TTSUnavailable(Exception):
    """No local voice (Piper not installed, model missing, turned off, or it failed)."""


def voices_dir() -> Path:
    return Path(os.environ.get("NETCHECK_TTS_DIR") or _ROOT / "voices" / "piper").expanduser()


def _pace() -> float:
    try:
        return min(2.0, max(0.7, float(os.environ.get("NETCHECK_TTS_SLOW", "1.2"))))
    except ValueError:
        return 1.2


def model_path(lang: str) -> Path:
    return voices_dir() / f"{VOICES.get(lang, VOICES['en'])}.onnx"


def available(lang: str = "ro") -> bool:
    if os.environ.get("NETCHECK_TTS", "local").lower() == "off":
        return False
    try:
        import piper  # noqa: F401
    except Exception:  # noqa: BLE001 - not installed (or broken install): the app falls back
        return False
    p = model_path(lang)
    return p.is_file() and Path(str(p) + ".json").is_file()


_cache: dict[str, object] = {}
_lock = threading.Lock()


def _voice(lang: str):
    path = model_path(lang)
    with _lock:
        if str(path) not in _cache:
            from piper import PiperVoice
            _cache[str(path)] = PiperVoice.load(str(path))
        return _cache[str(path)]


def synthesize(text: str, lang: str = "ro") -> bytes:
    """Speech for one short answer, as a WAV file (bytes). Raises TTSUnavailable."""
    lang = lang if lang in VOICES else "ro"
    text = (text or "").strip()[:MAX_CHARS]
    if not text:
        raise TTSUnavailable("nothing to say")
    if not available(lang):
        raise TTSUnavailable("no local voice for " + lang)
    try:
        voice = _voice(lang)
        buf = io.BytesIO()
        with _lock, wave.open(buf, "wb") as wav:
            try:                                     # piper-tts >= 1.3
                from piper import SynthesisConfig
                voice.synthesize_wav(text, wav, syn_config=SynthesisConfig(length_scale=_pace()))
            except ImportError:                      # piper-tts 1.2
                voice.synthesize(text, wav, length_scale=_pace(), sentence_silence=0.35)
        data = buf.getvalue()
    except TTSUnavailable:
        raise
    except Exception as e:  # noqa: BLE001 - any engine error: the page uses another voice
        raise TTSUnavailable(f"piper failed: {e.__class__.__name__}") from None
    if len(data) <= 44:                              # header only, no sound
        raise TTSUnavailable("piper produced no audio")
    return data


def status() -> dict:
    return {"ro": available("ro"), "en": available("en"), "dir": str(voices_dir())}


def describe() -> Optional[str]:
    s = status()
    on = [k for k in ("ro", "en") if s[k]]
    return f"local voice (Piper): {', '.join(on)}" if on else None
