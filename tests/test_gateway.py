"""Gateway end-to-end with fake model backends (no API key, no GPU, localhost only)."""
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from gateway.backends import BackendError, ClaudeBackend, OllamaBackend, make_backend
from gateway.config import Config
from gateway.server import make_server
from netcheck.ai.assistant import ask
from netcheck.ai.contract import ContractError, build_request, validate_request
from netcheck.ai.remote import RemoteProvider
from netcheck.core.analysis import analyze_file

FIX = Path(__file__).parent / "fixtures" / "synthetic"
FAKE_KEY = "test-key-not-real"


class FakeBackend:
    name = "fake"

    def __init__(self, replies=None, error=None):
        self.replies = list(replies or [])
        self.error = error
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        if self.error:
            raise BackendError(self.error)
        return self.replies.pop(0) if self.replies else "Your network score is 40."

    def health(self):
        return {"backend": self.name, "configured": True}


class JsonServer:
    """Tiny scripted HTTP server: records requests, returns `reply(path, body, headers)`."""

    def __init__(self, reply):
        self.requests = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _reply(self, body):
                status, payload = reply(self.path, body, dict(self.headers))
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._reply(None)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append((self.path, body, dict(self.headers)))
                self._reply(body)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"


def start(cfg, backend):
    gw = make_server(cfg, backend)
    threading.Thread(target=gw.serve_forever, daemon=True).start()
    return gw, f"http://127.0.0.1:{gw.server_address[1]}"


@pytest.fixture()
def gw():
    backend = FakeBackend()
    cfg = Config(port=0, rate_per_min=5, anthropic_api_key=FAKE_KEY)
    srv, url = start(cfg, backend)
    yield backend, url, cfg
    srv.shutdown()


@pytest.fixture(scope="module")
def v2():
    return analyze_file(FIX / "V2_smart_home.xml")


def _post(url, payload=None, raw=None, headers=None):
    data = raw if raw is not None else json.dumps(payload).encode()
    req = urllib.request.Request(url + "/v1/ask", data=data, method="POST",
                                 headers={"content-type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ------------------------------------------------------------------ end to end
def test_end_to_end_answer(gw, v2):
    backend, url, _ = gw
    backend.replies = ["Cel mai periculos este camera 192.168.1.40. Schimbă parola din fabrică."]
    ans = ask("Ce repar primul?", v2, "ro", provider=RemoteProvider(url=url))
    assert ans.source == "ai" and "192.168.1.40" in ans.text
    system, user = backend.calls[0][0], backend.calls[0][1]
    assert system["role"] == "system" and "DOAR" in system["content"] and "DATE (rezultatul" in system["content"]
    assert user == {"role": "user", "content": "Ce repar primul?"}


def test_health(gw):
    _, url, _ = gw
    with urllib.request.urlopen(url + "/health", timeout=5) as r:
        h = json.loads(r.read())
    assert h["ok"] and h["backend"] == "fake"
    assert RemoteProvider(url=url).status()["online"] is True


# ------------------------------------------------------------------ backends
def test_claude_backend_request_format():
    api = JsonServer(lambda path, body, h: (200, {"content": [{"type": "text", "text": "Scor 40."}],
                                                  "stop_reason": "end_turn"}))
    try:
        cfg = Config(anthropic_api_key=FAKE_KEY, claude_model="claude-haiku-5-5", max_output_tokens=123)
        b = ClaudeBackend(cfg, url=api.url + "/v1/messages")
        out = b.complete([{"role": "system", "content": "SYS"}, {"role": "user", "content": "Q"}])
        assert out == "Scor 40."
        path, body, headers = api.requests[0]
        lower = {k.lower(): v for k, v in headers.items()}
        assert lower["x-api-key"] == FAKE_KEY and lower["anthropic-version"] == "2023-06-01"
        assert body["system"] == "SYS" and body["messages"] == [{"role": "user", "content": "Q"}]
        assert body["model"] == "claude-haiku-5-5" and body["max_tokens"] == 123
        # Haiku 5.5 thinks by default and thinking eats max_tokens -> we turn it off
        assert body["thinking"] == {"type": "disabled"} and body["output_config"] == {"effort": "low"}
        assert "temperature" not in body   # non-default sampling params are rejected by Haiku 5.5
    finally:
        api.srv.shutdown()


def test_claude_backend_errors_do_not_leak():
    api = JsonServer(lambda p, b, h: (401, {"error": {"message": "invalid x-api-key " + FAKE_KEY}}))
    try:
        b = ClaudeBackend(Config(anthropic_api_key=FAKE_KEY), url=api.url + "/v1/messages")
        with pytest.raises(BackendError) as e:
            b.complete([{"role": "user", "content": "Q"}])
        assert str(e.value).startswith("claude HTTP 401") and FAKE_KEY not in str(e.value)
        assert "invalid x-api-key" in str(e.value)   # the reason is shown, the key is redacted
    finally:
        api.srv.shutdown()


def test_ollama_backend_optional():
    api = JsonServer(lambda p, b, h: (200, {"message": {"content": "<think>x</think>Scor 40."},
                                            "models": [{"name": "m"}]}))
    try:
        cfg = Config(backend="ollama", ollama_url=api.url, ollama_model="m")
        b = make_backend(cfg)
        assert isinstance(b, OllamaBackend) and b.complete([{"role": "user", "content": "Q"}]) == "Scor 40."
        assert api.requests[0][1]["think"] is False
        assert b.health()["configured"] is True
    finally:
        api.srv.shutdown()


def test_key_never_printed():
    cfg = Config(anthropic_api_key=FAKE_KEY, token="tok-secret")
    assert FAKE_KEY not in repr(cfg) and FAKE_KEY not in cfg.describe() and "tok-secret" not in repr(cfg)
    assert FAKE_KEY not in repr(ClaudeBackend(cfg))


def test_gateway_refuses_to_start_without_key():
    with pytest.raises(SystemExit):
        make_server(Config(port=0, backend="claude", anthropic_api_key=""))


def test_refuses_public_bind_without_token():
    with pytest.raises(SystemExit):
        make_server(Config(host="0.0.0.0", port=0), FakeBackend())


# ------------------------------------------------------------------ privacy / contract
def test_context_has_no_hostnames_or_macs(v2):
    blob = json.dumps(build_request("q", v2, "ro"))
    assert "ipcam.lan" not in blob and "router.lan" not in blob       # hostnames stay local
    assert "C0:56:E3" not in blob and ":XX:" not in blob              # no MAC at all, not even masked


def test_gateway_drops_unknown_fields_and_fixes_severity(v2):
    req = build_request("q", v2, "en")
    req["context"]["devices"][0]["hostname"] = "secret-laptop"
    req["context"]["findings"][0]["severity"] = "info"
    _, _, ctx, _ = validate_request(req)
    assert "hostname" not in ctx["devices"][0]
    assert ctx["findings"][0]["severity"] == "high"


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(v=2),
    lambda r: r.update(lang="fr"),
    lambda r: r.update(question=""),
    lambda r: r["context"]["devices"][0].update(ip="8.8.8.8"),          # public IPs are never ours
    lambda r: r["context"]["findings"][0].update(code="MADE_UP"),
    lambda r: r["context"].update(devices=[{}] * 1000),
])
def test_contract_rejects_bad_requests(v2, mutate):
    req = build_request("q", v2, "en")
    mutate(req)
    with pytest.raises(ContractError):
        validate_request(req)


# ------------------------------------------------------------------ grounding
def test_ungrounded_answer_is_retried_then_accepted(gw, v2):
    backend, url, _ = gw
    backend.replies = ["Close port 3389 now.", "The camera at 192.168.1.40 streams video."]
    ans = ask("?", v2, "en", provider=RemoteProvider(url=url))
    assert ans.source == "ai" and "3389" not in ans.text
    assert "previous answer" in backend.calls[1][-1]["content"]


def test_ungrounded_twice_falls_back(gw, v2):
    backend, url, _ = gw
    backend.replies = ["Call +40 721 123 456.", "See CVE-2024-1234."]
    ans = ask("?", v2, "en", provider=RemoteProvider(url=url))
    assert ans.source == "fallback" and "ungrounded" in ans.reason
    assert "Network score: 40/100" in ans.text


# ------------------------------------------------------------------ protections
def test_rejects_bad_json_and_wrong_type(gw):
    _, url, _ = gw
    assert _post(url, raw=b"{not json")[0] == 400
    req = urllib.request.Request(url + "/v1/ask", data=b"{}", method="POST", headers={"content-type": "text/plain"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=5)
    assert e.value.code == 415


def test_body_too_large(gw):
    _, url, cfg = gw
    assert _post(url, raw=b"x" * (cfg.max_body + 1))[0] == 413


def test_rate_limit(gw, v2):
    _, url, cfg = gw
    req = build_request("q", v2, "en")
    codes = [_post(url, req)[0] for _ in range(cfg.rate_per_min + 2)]
    assert codes[:cfg.rate_per_min] == [200] * cfg.rate_per_min and codes[-1] == 429


def test_daily_limit_protects_credits(v2):
    backend = FakeBackend()
    srv, url = start(Config(port=0, daily_limit=2, rate_per_min=0), backend)
    try:
        req = build_request("q", v2, "en")
        codes = [_post(url, req) for _ in range(3)]
        assert [c for c, _ in codes] == [200, 200, 503] and codes[2][1]["error"] == "daily_limit"
        assert len(backend.calls) == 2
    finally:
        srv.shutdown()


def test_token_required_when_configured(v2):
    srv, url = start(Config(port=0, token="s3cret-test-token"), FakeBackend())
    try:
        assert ask("q", v2, "en", provider=RemoteProvider(url=url, token="")).reason.startswith("gateway HTTP 401 (unauthorized)")
        assert ask("q", v2, "en", provider=RemoteProvider(url=url, token="s3cret-test-token")).source == "ai"
    finally:
        srv.shutdown()


def test_model_down_gives_503_and_client_falls_back(v2):
    srv, url = start(Config(port=0), FakeBackend(error="claude unreachable: URLError"))
    try:
        status, body = _post(url, build_request("q", v2, "en"))
        assert status == 503 and body["error"] == "model_unavailable"
        assert ask("q", v2, "en", provider=RemoteProvider(url=url)).source == "fallback"
    finally:
        srv.shutdown()


def test_gateway_down_falls_back_fast(v2):
    ans = ask("q", v2, "ro", provider=RemoteProvider(url="http://127.0.0.1:9", timeout=3))
    assert ans.source == "fallback" and "unreachable" in ans.reason


def test_client_refuses_plain_http_to_remote_host():
    from netcheck.ai.providers import LLMUnavailable
    with pytest.raises(LLMUnavailable):
        RemoteProvider(url="http://example.com")
    with pytest.raises(LLMUnavailable):
        RemoteProvider(url="http://localhost.evil.com")


def test_fallback_mentions_changes():
    before, after = analyze_file(FIX / "V6a_before.xml"), analyze_file(FIX / "V6b_after.xml")
    ans = ask("ce s-a schimbat?", after, "ro", previous=before,
              provider=RemoteProvider(url="http://127.0.0.1:9", timeout=2))
    assert "scor 60 → 100, 3 probleme rezolvate" in ans.text


def test_local_gateway_ignores_system_proxy(gw, v2, monkeypatch):
    """Windows urllib picks up the system proxy; a local gateway must bypass it."""
    _, url, _ = gw
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    assert ask("q", v2, "en", provider=RemoteProvider(url=url)).source == "ai"


def test_unreachable_message_says_why(v2):
    ans = ask("q", v2, "en", provider=RemoteProvider(url="http://127.0.0.1:9", timeout=3))
    assert "127.0.0.1:9" in ans.reason and ("refused" in ans.reason.lower() or "errno" in ans.reason)


# ------------------------------------------------------------------ conversation
def test_conversation_through_gateway(gw, v2):
    from netcheck.ai.assistant import Conversation
    backend, url, _ = gw
    backend.replies = ["Camera 192.168.1.40 este cea mai riscantă.", "Primul pas: schimbă parola din fabrică."]
    conv = Conversation(v2, "ro", provider=RemoteProvider(url=url))
    assert conv.ask("Care e cel mai periculos dispozitiv?").source == "ai"
    assert conv.ask("Și ce fac prima dată cu ea?").source == "ai"
    second = backend.calls[1]
    assert [m["role"] for m in second] == ["system", "user", "assistant", "user"]
    assert second[2]["content"] == "Camera 192.168.1.40 este cea mai riscantă."
    assert second[3]["content"] == "Și ce fac prima dată cu ea?"


@pytest.mark.parametrize("history", [
    [{"role": "assistant", "content": "x"}],                                   # must start with user
    [{"role": "user", "content": "x"}],                                        # must end with assistant
    [{"role": "user", "content": "a"}, {"role": "system", "content": "b"}],    # no system injection
    [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}] * 7,   # too long
])
def test_contract_rejects_bad_history(v2, history):
    req = build_request("q", v2, "en")
    req["history"] = history
    with pytest.raises(ContractError):
        validate_request(req)


def test_model_error_reason_reaches_the_app(v2):
    srv, url = start(Config(port=0), FakeBackend(error="claude HTTP 400 (invalid_request_error: credit balance is too low)"))
    try:
        ans = ask("q", v2, "en", provider=RemoteProvider(url=url))
        assert ans.source == "fallback" and "credit balance is too low" in ans.reason
    finally:
        srv.shutdown()


def _claude_reply(payload):
    api = JsonServer(lambda p, b, h: (200, payload))
    b = ClaudeBackend(Config(anthropic_api_key=FAKE_KEY), url=api.url + "/v1/messages")
    try:
        return b.complete([{"role": "user", "content": "Q"}])
    finally:
        api.srv.shutdown()


def test_cut_off_answer_is_trimmed_to_last_sentence():
    out = _claude_reply({"stop_reason": "max_tokens", "content": [
        {"type": "text", "text": "Scorul este 40. Camera e cea mai riscantă. Hub-ul inte"}]})
    assert out == "Scorul este 40. Camera e cea mai riscantă."


def test_answer_with_only_thinking_is_reported_clearly():
    with pytest.raises(BackendError) as e:
        _claude_reply({"stop_reason": "max_tokens", "content": [{"type": "thinking", "thinking": ""}]})
    assert "no text" in str(e.value) and "max_tokens" in str(e.value)


def test_markdown_is_stripped(gw, v2):
    backend, url, _ = gw
    backend.replies = ["## Rezumat\nRețeaua are scorul **40**, adică __Risc ridicat__."]
    ans = ask("?", v2, "ro", provider=RemoteProvider(url=url))
    assert ans.text == "Rezumat\nRețeaua are scorul 40, adică Risc ridicat."


def test_prompt_rules():
    from gateway.prompts import SYSTEM
    for lang in ("ro", "en"):
        assert "Markdown" in SYSTEM[lang] and "JSON" in SYSTEM[lang]
