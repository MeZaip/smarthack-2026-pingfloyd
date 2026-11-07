"""Built-in RO/EN explanations and fixes (FR-07/FR-08). Always available, no network."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LANGS = ("ro", "en")


@lru_cache(maxsize=1)
def _texts() -> dict:
    return json.loads((Path(__file__).parent / "texts.json").read_text(encoding="utf-8"))


def get(code: str, lang: str = "ro") -> dict:
    lang = lang if lang in LANGS else "ro"
    entry = _texts().get(code)
    if not entry:
        return {"title": code, "explain": "", "steps": [], "refs": []}
    return {**entry[lang], "refs": entry.get("refs", [])}


def all_codes() -> list[str]:
    return list(_texts().keys())


SEVERITY_LABEL = {
    "ro": {"high": "Ridicat", "medium": "Mediu", "low": "Scăzut", "info": "Informativ"},
    "en": {"high": "High", "medium": "Medium", "low": "Low", "info": "Info"},
}
SEVERITY_ICON = {"high": "⛔", "medium": "⚠️", "low": "🔹", "info": "ℹ️"}


def score_band(score: int | None, lang: str = "ro") -> tuple[str, str, str]:
    """(css class, icon, label) — colour is never the only signal (NFR-08)."""
    if score is None:
        return ("err", "✖", "Fișier ilizibil" if lang == "ro" else "Unreadable file")
    if score >= 80:
        return ("good", "✔", "Bine" if lang == "ro" else "Good")
    if score >= 50:
        return ("warn", "⚠", "Atenție" if lang == "ro" else "Needs attention")
    return ("bad", "⛔", "Risc mare" if lang == "ro" else "High risk")
