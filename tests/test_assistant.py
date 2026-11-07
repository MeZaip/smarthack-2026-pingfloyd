"""AI assistant: tool loop, grounding guard and fallback - with a fake provider (no network)."""
from pathlib import Path

import pytest

from netcheck.ai.assistant import ask
from netcheck.ai.grounding import GroundingError, check
from netcheck.ai.providers import LLMUnavailable, NoProvider
from netcheck.core.analysis import analyze_file

V2 = Path(__file__).parent / "fixtures" / "synthetic" / "V2_smart_home.xml"


class FakeProvider:
    """Replays scripted responses and records what it was sent."""
    name = "fake"

    def __init__(self, final_text, use_tool="get_summary"):
        self.final_text = final_text
        self.use_tool = use_tool
        self.calls = []

    def create(self, *, system, messages, tools, max_tokens=700):
        self.calls.append(messages)
        if len(self.calls) == 1 and self.use_tool:
            return {"stop_reason": "tool_use", "content": [
                {"type": "text", "text": "Let me check."},
                {"type": "tool_use", "id": "toolu_1", "name": self.use_tool, "input": {}},
            ]}
        return {"stop_reason": "end_turn", "content": [{"type": "text", "text": self.final_text}]}


class DownProvider:
    name = "down"

    def create(self, **_):
        raise LLMUnavailable("network error: URLError")


@pytest.fixture(scope="module")
def v2():
    return analyze_file(V2)


def test_grounded_answer_passes(v2):
    p = FakeProvider("Cel mai periculos este camera 192.168.1.40, care trimite video pe portul 554.")
    ans = ask("Care e cel mai periculos dispozitiv?", v2, "ro", provider=p)
    assert ans.source == "ai" and ans.tools_used == ["get_summary"]
    # the tool result was sent back with the matching id
    tool_result = p.calls[1][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "toolu_1"
    assert "192.168.1.40" in tool_result["content"]


@pytest.mark.parametrize("bad", [
    "Device 192.168.1.77 is dangerous.",            # IP not in scan
    "Close port 3389 on the router.",                # port not in scan
    "This is CVE-2021-44228.",                       # invented CVE
    "Call support at +40 721 123 456.",              # invented phone
    "See https://example.com/fix for help.",         # external link
])
def test_ungrounded_answers_fall_back(v2, bad):
    ans = ask("question", v2, "en", provider=FakeProvider(bad))
    assert ans.source == "fallback" and ans.reason.startswith("grounding")
    assert "Network score: 40/100" in ans.text


def test_offline_falls_back_with_useful_answer(v2):
    ans = ask("Ce fac primul?", v2, "ro", provider=DownProvider())
    assert ans.source == "fallback"
    assert "Cel mai periculos dispozitiv: 192.168.1.40" in ans.text
    assert "Primul pas:" in ans.text


def test_disabled_ai(v2):
    assert ask("x", v2, "en", provider=NoProvider()).source == "fallback"


def test_check_allows_scan_facts(v2):
    check("Router 192.168.1.1 has UPnP on port 1900 and an admin page at http://192.168.1.1", v2)
    with pytest.raises(GroundingError):
        check("open 192.168.1.1:8080", v2)


def test_mac_is_masked_in_tools(v2):
    from netcheck.ai.assistant import ScanTools
    devs = ScanTools(v2, "en").list_devices()
    assert all(d["mac"] is None or d["mac"].endswith(":XX:XX:XX") for d in devs)


def test_template_wording_with_bare_scheme_is_allowed(v2):
    check("Adresa începe cu http://, fără „s”, deci folosește https:// în loc.", v2)
