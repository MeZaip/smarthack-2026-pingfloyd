"""Client-side assistant: local grounding re-check and built-in fallback (no network)."""
from pathlib import Path

import pytest

from netcheck.ai.assistant import ScanTools, ask
from netcheck.ai.grounding import GroundingError, check
from netcheck.ai.providers import LLMUnavailable, NoProvider
from netcheck.core.analysis import analyze_file

V2 = Path(__file__).parent / "fixtures" / "synthetic" / "V2_smart_home.xml"


class FakeGateway:
    """Stands in for RemoteProvider."""
    kind = "remote"
    name = "fake-gateway"

    def __init__(self, text=None, error=None):
        self.text, self.error, self.calls = text, error, []

    def answer(self, question, analysis, lang, previous=None, history=None):
        self.calls.append((question, lang))
        self.histories = getattr(self, "histories", []) + [list(history or [])]
        if self.error:
            raise LLMUnavailable(self.error)
        return self.text


@pytest.fixture(scope="module")
def v2():
    return analyze_file(V2)


def test_grounded_answer_passes(v2):
    p = FakeGateway("Cel mai periculos este camera 192.168.1.40, care trimite video pe portul 554.")
    ans = ask("Care e cel mai periculos dispozitiv?", v2, "ro", provider=p)
    assert ans.source == "ai" and p.calls == [("Care e cel mai periculos dispozitiv?", "ro")]


@pytest.mark.parametrize("bad", [
    "Device 192.168.1.77 is dangerous.",            # IP not in scan
    "Close port 3389 on the router.",                # port not in scan
    "This is CVE-2021-44228.",                       # invented CVE
    "Call support at +40 721 123 456.",              # invented phone
    "See https://example.com/fix for help.",         # external link
])
def test_ungrounded_answers_fall_back_even_if_gateway_missed_them(v2, bad):
    ans = ask("question", v2, "en", provider=FakeGateway(bad))
    assert ans.source == "fallback" and ans.reason.startswith("grounding")
    assert "Network score: 40/100" in ans.text


def test_gateway_down_gives_useful_built_in_answer(v2):
    ans = ask("Ce fac primul?", v2, "ro", provider=FakeGateway(error="gateway unreachable: URLError"))
    assert ans.source == "fallback"
    assert "Cel mai periculos dispozitiv: 192.168.1.40" in ans.text
    assert "Primul pas:" in ans.text


def test_disabled_ai(v2):
    assert ask("x", v2, "en", provider=NoProvider()).source == "fallback"


def test_empty_question_does_not_call_gateway(v2):
    p = FakeGateway("x")
    assert ask("   ", v2, "en", provider=p).source == "fallback" and p.calls == []


def test_check_allows_scan_facts(v2):
    check("Router 192.168.1.1 has UPnP on port 1900 and an admin page at http://192.168.1.1", v2)
    with pytest.raises(GroundingError):
        check("open 192.168.1.1:8080", v2)


def test_template_wording_with_bare_scheme_is_allowed(v2):
    check("Adresa începe cu http://, fără „s”, deci folosește https:// în loc.", v2)


def test_mac_is_masked_in_views(v2):
    devs = ScanTools(v2, "en").list_devices()
    assert all(d["mac"] is None or d["mac"].endswith(":XX:XX:XX") for d in devs)


def test_app_has_no_api_key_code():
    """The client must never need or read an API key."""
    root = Path(__file__).resolve().parent.parent / "netcheck"
    for f in root.rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY" not in text and "x-api-key" not in text, f


def test_conversation_keeps_only_ai_turns(v2):
    from netcheck.ai.assistant import Conversation
    p = FakeGateway("Scorul rețelei este 40.")
    conv = Conversation(v2, "ro", provider=p)
    conv.ask("Care e scorul?")
    conv.ask("Și ce înseamnă asta?")
    assert p.histories[0] == []
    assert p.histories[1] == [{"role": "user", "content": "Care e scorul?"},
                              {"role": "assistant", "content": "Scorul rețelei este 40."}]
    p.error = "gateway down"
    conv.ask("Încă una?")                       # fallback answers are not added to history
    assert len(conv.history) == 4
    conv.reset()
    assert conv.history == []


def test_conversation_history_is_bounded(v2):
    from netcheck.ai.assistant import Conversation
    conv = Conversation(v2, "en", provider=FakeGateway("Score is 40."))
    for i in range(20):
        conv.ask(f"question {i}")
    assert len(conv.history) == 2 * Conversation.MAX_TURNS
