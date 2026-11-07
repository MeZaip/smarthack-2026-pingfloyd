"""Voice mode helpers (FR-12 by voice): turn an assistant answer into something good to hear.

A voice answer must not read addresses or technical numbers digit by digit ("192.168.1.1", "1900/udp",
"XX:XX:XX:XX:1A:2B"). The voice prompt already asks the model for that; this is the safety net, used
by the gateway before text-to-speech and by the app for the built-in (offline) voice answer.
It never adds facts: it only removes addresses / numbers, list markers and Markdown, and keeps the first
few sentences.
"""
from __future__ import annotations

import re

STYLES = ("text", "voice")
MAX_TTS_CHARS = 600                 # one spoken answer; longer text is cut at a sentence end

_PAREN_TECH = re.compile(r"\s*\((?=[^()]*(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[0-9A-FX]{2}:[0-9A-FX]{2}:|/(?:tcp|udp)\b))[^()]*\)", re.I)
_IP_PORT = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b")
_MAC = re.compile(r"\b(?:[0-9A-FX]{2}:){5}[0-9A-FX]{2}\b", re.I)
_PORT_PROTO = re.compile(r"\b\d{1,5}\s*/\s*(?:tcp|udp)\b", re.I)
_PORT_WORD = {
    "ro": re.compile(r"\b(?:portul|portului|port|ușa|usa)\s+(?:nr\.?\s*)?\d{1,5}\b", re.I),
    "en": re.compile(r"\b(?:port|door)\s+(?:no\.?\s*)?\d{1,5}\b", re.I),
}
_A_DOOR = {"ro": "o ușă", "en": "a door"}
_CODE = re.compile(r"\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b")          # finding codes like TELNET_OPEN
_MD = re.compile(r"\*\*|__|`|^#+\s*", re.M)
_STEP = re.compile(r"^\s*(?:\d+[.)]|[-•*])\s+", re.M)
_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")          # a dot inside 192.168.1.1 is not a sentence end


def _scrub(t: str, lang: str) -> str:
    t = _PORT_WORD[lang].sub(_A_DOOR[lang], t)
    # the little word in front of an address or code goes too: "at 192.168.1.40" / "de la 192..." / "Code TELNET_OPEN"
    t = re.sub(r"\b(?:at|on|from|de la|la|pe|cu|ip|mac)\s+(?=(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9A-FX]{2}:){5})", "", t, flags=re.I)
    t = re.sub(r"\b(?:code|cod(?:ul)?)\s*:?\s*(?=[A-Z][A-Z0-9]+_)", "", t, flags=re.I)
    for rx in (_PORT_PROTO, _MAC, _IP_PORT, _CODE):
        t = rx.sub("", t)
    t = re.sub(r"\(\s*[,;:]?\s*\)", "", t)                       # "( )" left behind
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)                        # "la ." -> "la."
    t = re.sub(r"[,;:]\s*([.!?])", r"\1", t)
    t = re.sub(r"([.!?])(?:\s*\.)+", r"\1", t)                    # a sentence that became empty
    return re.sub(r"\s+", " ", t).strip()


def _technical(s: str) -> bool:
    return any(rx.search(s) for rx in (_IP_PORT, _MAC, _PORT_PROTO, _CODE)) or bool(_PORT_WORD["ro"].search(s) or _PORT_WORD["en"].search(s))


def to_speech_text(text: str, lang: str = "ro", max_sentences: int = 3, max_chars: int = MAX_TTS_CHARS) -> str:
    """Plain, short, speakable text: no IPs, MACs, port numbers, codes, lists or Markdown.
    Technical sentences are left out whole (cutting a number out of a sentence breaks its grammar);
    only when nothing else is left are they kept with the numbers removed."""
    lang = lang if lang in _A_DOOR else "ro"
    t = _MD.sub("", str(text or ""))
    t = _STEP.sub("", t)
    t = _PAREN_TECH.sub("", t)
    t = re.sub(r"\s+", " ", t.replace("\n", " ")).strip()
    split = lambda x: [y.strip() for y in _SENT_SPLIT.split(x) if y.strip() and re.search(r"\w", y)]
    keep = [x for x in split(t) if not _technical(x)]
    if not keep:
        keep = [y for y in split(_scrub(t, lang)) if re.search(r"\w{2}", y)]
    out = ""
    for x in keep[:max_sentences]:
        if out and len(out) + 1 + len(x) > max_chars:
            break
        out = f"{out} {x}".strip()
    return out[:max_chars].strip()
