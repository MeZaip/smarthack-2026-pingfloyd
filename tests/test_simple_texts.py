"""Beginner texts (children, older people): complete, short, and free of technical words where it matters."""
import re

import pytest

from netcheck.explain.simple_texts import GLOSSARY, SIMPLE, WHO
from netcheck.explain.texts import TEXTS

ACRONYM = re.compile(r"\b[A-Z]{2,}[a-z]*[A-Z]*\b")          # RTSP, UPnP, SSH, IP ...
JARGON = re.compile(r"\b(port|porturi|ip|tcp|udp|protocol|server|serviciu|service|criptat|encrypt\w*)\b", re.I)


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def test_every_catalog_code_has_a_beginner_text():
    assert set(SIMPLE) == set(TEXTS)


@pytest.mark.parametrize("code", sorted(SIMPLE))
@pytest.mark.parametrize("lang", ["ro", "en"])
def test_beginner_text_is_short_and_plain(code, lang):
    t = SIMPLE[code][lang]
    assert SIMPLE[code]["who"] in WHO
    assert not ACRONYM.search(t["title"]), t["title"]
    assert not JARGON.search(t["title"]), t["title"]
    assert not ACRONYM.search(t["explain"].replace("Wi-Fi", "")), t["explain"]
    assert not JARGON.search(t["explain"]), t["explain"]
    assert 1 <= len(_sentences(t["explain"])) <= 2
    assert 1 <= len(t["steps"]) <= 3
    assert all(len(s) <= 120 for s in t["steps"])


def test_glossary_in_both_languages():
    assert len(GLOSSARY["ro"]) == len(GLOSSARY["en"]) >= 5
