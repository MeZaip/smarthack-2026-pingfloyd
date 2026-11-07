"""Which language a question is written in (Romanian or English), so the assistant answers in it,
whatever language the page is set to. Small word lists, no outside service, no guessing beyond RO/EN."""
from __future__ import annotations

import re

_RO_LETTERS = re.compile(r"[ăâîșşțţ]", re.I)
_WORD = re.compile(r"[a-zăâîșşțţ']+", re.I)
RO_WORDS = {
    "ce", "cum", "care", "este", "e", "sunt", "si", "și", "sa", "să", "nu", "da", "de", "la", "pe", "cu", "din",
    "pentru", "mea", "meu", "mele", "mei", "am", "ai", "are", "fac", "repar", "reparat", "prima", "primul", "data",
    "dată", "unde", "cine", "cand", "când", "cat", "cât", "poate", "pot", "trebuie", "aparat", "aparate",
    "aparatul", "dispozitiv", "dispozitive", "retea", "rețea", "reteaua", "rețeaua", "parola", "parolă",
    "imprimanta", "imprimantă", "camera", "cameră", "scor", "scorul", "periculos", "sigur", "sigură", "asta",
    "acum", "mai", "foarte", "vreau", "spune", "spune-mi", "explica", "explică", "inseamna", "înseamnă",
    "deschis", "deschisă", "usa", "ușa", "casa", "casă", "salut", "buna", "bună", "multumesc", "mulțumesc",
}
EN_WORDS = {
    "what", "how", "which", "is", "are", "the", "a", "an", "and", "to", "of", "in", "on", "with", "for", "my",
    "me", "i", "do", "does", "should", "can", "could", "fix", "first", "where", "who", "when", "why", "device",
    "devices", "network", "password", "printer", "camera", "score", "dangerous", "safe", "this", "that", "now",
    "more", "very", "want", "tell", "explain", "mean", "means", "open", "door", "house", "home", "hi", "hello",
    "thanks", "thank", "you", "it", "there", "have", "has", "need", "please",
}


def detect(text: str, default: str = "ro") -> str:
    """'ro' or 'en' for the question; `default` (the page language) when it cannot tell."""
    text = text or ""
    ro = 3 * len(_RO_LETTERS.findall(text))           # Romanian letters are a strong sign
    en = 0
    for w in _WORD.findall(text.lower()):
        if w in RO_WORDS:
            ro += 1
        if w in EN_WORDS:
            en += 1
    if ro > en:
        return "ro"
    if en > ro:
        return "en"
    return default if default in ("ro", "en") else "ro"
