"""Voice mode of the assistant: short spoken answers without addresses, the gateway's optional natural
voice (/v1/tts, key only on the gateway) and the app endpoint /api/v1/tts with its browser-voice fallback."""
import json
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from gateway.config import Config
from gateway.prompts import VOICE, build_messages
from gateway.server import make_server
from netcheck.ai import assistant
from netcheck.ai.assistant import ScanTools, ask, voice_fallback
from netcheck.ai.contract import build_request, request_style, validate_request
from netcheck.ai.providers import LLMUnavailable
from netcheck.ai.remote import RemoteProvider
from netcheck.ai.voice import to_speech_text
from netcheck.core.analysis import analyze_file

FIX = Path(__file__).parent / "fixtures" / "synthetic"
TECH = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[0-9A-FX]{2}:[0-9A-FX]{2}:|\d+/(tcp|udp)|[A-Z]+_[A-Z_]+")


@pytest.fixture(scope="module")
def v2():
    return analyze_file(FIX / "V2_smart_home.xml")


# ------------------------------------------------------------------ speakable text
@pytest.mark.parametrize("text,lang,want,gone", [
    ("Cea mai mare problemă e la routerul TP-Link (192.168.1.1). Portul 80 e deschis.\n1. Intră în setări.\n2. Pune o parolă.",
     "ro", "Cea mai mare problemă e la routerul TP-Link. Intră în setări. Pune o parolă.", "192"),
    ("The camera at 192.168.1.40:554 streams video. Code CAMERA_STREAM_EXPOSED.", "en", "The camera streams video.", "554"),
    ("**Bine.** MAC XX:XX:XX:XX:0D:65 e ascuns. Totul e în regulă.", "ro", "Bine. Totul e în regulă.", "XX:"),
])
def test_speech_text_has_no_addresses_numbers_or_lists(text, lang, want, gone):
    out = to_speech_text(text, lang)
    assert out == want and gone not in out and not TECH.search(out)


def test_speech_text_keeps_at_most_three_sentences():
    assert to_speech_text("Unu. Doi. Trei. Patru. Cinci.", "ro") == "Unu. Doi. Trei."


# ------------------------------------------------------------------ contract + prompt
def test_style_is_optional_and_only_voice_or_text(v2):
    plain = build_request("q", v2, "ro")
    voice = build_request("q", v2, "ro", style="voice")
    assert "style" not in plain and voice["style"] == "voice"
    assert request_style(voice) == "voice" and request_style(plain) == "text"
    assert request_style({"style": "shout"}) == "text"
    validate_request(voice)                       # the extra field does not break validation


@pytest.mark.parametrize("lang", ["ro", "en"])
def test_voice_prompt_adds_the_spoken_rules(lang):
    text = build_messages(lang, "q", {"devices": []}, style="text")[0]["content"]
    voice = build_messages(lang, "q", {"devices": []}, style="voice")[0]["content"]
    assert VOICE[lang] not in text and VOICE[lang] in voice
    assert ("IP" in VOICE[lang]) and ("3" in VOICE[lang])          # no addresses, at most 3 sentences


# ------------------------------------------------------------------ gateway
class FakeBackend:
    name = "fake"

    def __init__(self):
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        return "Am găsit două probleme la routerul tău TP-Link. Prima e să îi pui o parolă. Vrei să-ți spun unde apeși?"

    def health(self):
        return {"backend": self.name, "configured": True}


class FakeTTS:
    name = "fake-tts"

    def __init__(self):
        self.texts = []

    def speak(self, text, lang):
        self.texts.append((text, lang))
        return b"ID3fake-mp3"


def _start(tts=None):
    backend = FakeBackend()
    srv = make_server(Config(port=0, anthropic_api_key="test-key-not-real"), backend, tts)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}", backend


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def test_gateway_voice_style_reaches_the_model(v2):
    srv, url, backend = _start()
    try:
        status, _, body = _post(url + "/v1/ask", build_request("Ce repar?", v2, "ro", style="voice"))
        assert status == 200 and json.loads(body)["answer"].startswith("Am găsit")
        assert VOICE["ro"] in backend.calls[-1][0]["content"]
    finally:
        srv.shutdown()


def test_gateway_tts_off_by_default():
    srv, url, _ = _start()
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            _post(url + "/v1/tts", {"v": 1, "lang": "ro", "text": "Salut."})
        assert e.value.code == 503 and json.loads(e.value.read())["error"] == "tts_unavailable"
        health = json.loads(urllib.request.urlopen(url + "/health", timeout=5).read())
        assert health["tts"] is False
    finally:
        srv.shutdown()


def test_gateway_tts_sends_only_clean_text_and_returns_mp3():
    tts = FakeTTS()
    srv, url, _ = _start(tts)
    try:
        status, ctype, audio = _post(url + "/v1/tts", {"v": 1, "lang": "ro",
                                                        "text": "Routerul TP-Link (192.168.1.1) are o ușă deschisă. Portul 1900 e deschis."})
        assert status == 200 and ctype == "audio/mpeg" and audio == b"ID3fake-mp3"
        sent, lang = tts.texts[-1]
        assert lang == "ro" and "192.168" not in sent and "1900" not in sent and sent.startswith("Routerul TP-Link")
        with pytest.raises(urllib.error.HTTPError) as e:
            _post(url + "/v1/tts", {"v": 1, "lang": "de", "text": "x"})
        assert e.value.code == 400
    finally:
        srv.shutdown()


# ------------------------------------------------------------------ app side
def test_voice_falls_back_to_a_short_spoken_answer(v2):
    class Down:
        name = "down"

        def answer(self, *a, **k):
            raise LLMUnavailable("offline")

    a = ask("Ce repar prima dată?", v2, "ro", provider=Down(), style="voice")
    assert a.source == "fallback" and not TECH.search(a.text) and a.text.count(".") <= 3
    assert "puncte din 100" in a.text
    assert voice_fallback(ScanTools(v2, "en")).startswith("Your home scores")


def test_old_providers_without_voice_keep_working(v2):
    class Old:                                     # no "style" parameter (like the team's earlier fakes)
        name = "old"

        def answer(self, question, analysis, lang, previous=None, history=None):
            return "The camera is the biggest problem."

    assert ask("q", v2, "en", provider=Old()).text == "The camera is the biggest problem."


def test_remote_provider_passes_style_and_reads_audio(v2):
    tts = FakeTTS()
    srv, url, backend = _start(tts)
    try:
        p = RemoteProvider(url=url)
        assert p.answer("Ce repar?", v2, "ro", style="voice").startswith("Am găsit")
        assert VOICE["ro"] in backend.calls[-1][0]["content"]
        assert p.tts("Salut, sunt asistentul.", "ro") == b"ID3fake-mp3"
    finally:
        srv.shutdown()


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "history.sqlite"))
    monkeypatch.setenv("NETCHECK_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("NETCHECK_LLM_PROVIDER", "none")
    monkeypatch.setenv("NETCHECK_TTS", "off")        # tests decide which voice exists (Piper may be installed here)
    from netcheck.web.app import app
    c = TestClient(app)
    c.get("/")                                     # session cookie for POST
    return c


def test_api_tts_says_unavailable_without_a_gateway_voice(client):
    r = client.post("/api/v1/tts?lang=ro", json={"text": "Salut."})
    assert r.status_code == 503 and r.json()["error"]["code"] == "tts_unavailable"


def test_api_tts_returns_audio_from_the_gateway(client, monkeypatch):
    from netcheck.web import api_v1

    class Voice:
        def tts(self, text, lang):
            return b"ID3fake"

    monkeypatch.setattr(api_v1, "get_provider", lambda: Voice())
    r = client.post("/api/v1/tts?lang=en", json={"text": "Hello."})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg" and r.content == b"ID3fake"


def test_api_ask_accepts_voice_style(client, monkeypatch):
    from netcheck import history
    from netcheck.web import app as web

    web._cache.clear()
    with history.open_history() as conn:
        history.save(conn, analyze_file(FIX / "V2_smart_home.xml"))
    seen = {}

    class Fake:
        name = "fake"

        def answer(self, q, a, lang, previous=None, history=None, style="text"):
            seen["style"] = style
            return "The camera is the biggest problem."

    monkeypatch.setattr(assistant, "get_provider", lambda: Fake())
    r = client.post("/api/v1/ask?lang=en", json={"question": "What first?", "style": "voice"})
    assert r.status_code == 200 and r.json()["mode"] == "ai" and seen["style"] == "voice"
    assert client.post("/api/v1/ask", json={"question": "x", "style": "sing"}).status_code == 422


# ------------------------------------------------------------------ local natural voice (Piper, free, on this computer)
def test_local_voice_is_off_without_piper_or_models(tmp_path, monkeypatch):
    from netcheck.ai import local_tts
    monkeypatch.setenv("NETCHECK_TTS_DIR", str(tmp_path))
    assert local_tts.available("ro") is False
    with pytest.raises(local_tts.TTSUnavailable):
        local_tts.synthesize("Salut.", "ro")


def test_api_tts_prefers_the_local_voice(client, monkeypatch):
    from netcheck.ai import local_tts
    from netcheck.web import api_v1
    seen = {}

    def fake(text, lang):
        seen["text"], seen["lang"] = text, lang
        return b"RIFF....WAVEfake"

    monkeypatch.setattr(local_tts, "synthesize", fake)
    monkeypatch.setattr(api_v1, "get_provider", lambda: pytest.fail("the gateway must not be asked"))
    r = client.post("/api/v1/tts?lang=ro", json={"text": "Routerul tău (192.168.1.1) are o ușă deschisă. Pune o parolă."})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content.startswith(b"RIFF")
    assert seen["lang"] == "ro" and "192.168" not in seen["text"] and "Pune o parolă." in seen["text"]


def test_local_voice_pace_is_slow_by_default(monkeypatch):
    from netcheck.ai import local_tts
    monkeypatch.delenv("NETCHECK_TTS_SLOW", raising=False)
    assert local_tts._pace() > 1.0
    monkeypatch.setenv("NETCHECK_TTS_SLOW", "9")
    assert local_tts._pace() == 2.0


def test_every_script_of_the_page_is_served_by_the_app(client):
    """voice.js was once missing from the server's file list: the page loaded without its voice."""
    html = (Path(__file__).parents[1] / "ui" / "index.html").read_text(encoding="utf-8")
    scripts = [s for s in re.findall(r'<script src="([^"]+)"', html) if s != "data.js"]   # data.js: live data instead
    assert "voice.js" in scripts
    for src in scripts:
        assert client.get("/" + src).status_code == 200, src
