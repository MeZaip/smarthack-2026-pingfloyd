"""Grounded Q&A assistant (FR-12) - client side.

The app sends the question plus a minimal, privacy-preserving view of the scan
to the team's AI gateway (netcheck/ai/remote.py). The gateway holds the API key
and calls the model; the app holds no key. Every answer is checked again here
by the grounding guard. If the gateway is unreachable, slow, over its limits,
or the answer is not grounded, a deterministic built-in answer is returned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..core.analysis import Analysis
from ..core.device import DEVICE_LABELS
from ..core.diff import compare
from ..explain.texts import SEVERITY_LABELS, score_band, text_for
from .grounding import GroundingError, check
from .language import detect as detect_language
from .providers import LLMUnavailable, get_provider
from .voice import to_speech_text

MAX_QUESTION_CHARS = 1000
LANGS = ("ro", "en")


@dataclass
class Answer:
    text: str
    source: str                      # "ai" | "fallback"
    reason: Optional[str] = None     # why we fell back (for logs / UI badge)
    tools_used: list[str] = field(default_factory=list)


class ScanTools:
    """Read-only view over one analysis (and optionally the previous one); used for built-in answers and the UI."""

    def __init__(self, analysis: Analysis, lang: str = "ro", previous: Optional[Analysis] = None):
        if not analysis.ok:
            raise ValueError("cannot build tools for an unreadable scan")
        self.a = analysis
        self.prev = previous if previous and previous.ok else None
        self.lang = lang

    def _finding_dict(self, f) -> dict:
        t = text_for(f.code, self.lang)
        return {
            "ip": f.ip, "port": f.port, "protocol": f.protocol, "code": f.code,
            "severity": f.severity, "severity_label": SEVERITY_LABELS[f.severity][self.lang],
            "points": f.points, "evidence": f.evidence,
            "title": t["title"], "explanation": t["explain"], "fix_steps": t["steps"],
        }

    def get_summary(self) -> dict:
        band = score_band(self.a.score, self.lang)
        top = self.a.most_dangerous()
        first = self.a.prioritized()[0] if self.a.findings else None
        return {
            "file": self.a.file,
            "standard_score": self.a.score,
            "band": band["label"],
            "device_count": len(self.a.scan.up_hosts),
            "finding_count": len(self.a.findings),
            "most_dangerous_device": None if not top else {
                "ip": top["ip"], "type": DEVICE_LABELS[top["type"]][self.lang],
                "vendor": top["vendor"], "hostname": top["hostname"],
                "risk_points": top["risk_points"], "finding_codes": top["findings"],
            },
            "first_fix": self._finding_dict(first) if first else None,
        }

    def list_devices(self) -> list[dict]:
        devs = self.a.devices()
        for d in devs:
            d["type_label"] = DEVICE_LABELS[d["type"]][self.lang]
        return devs

    def get_device(self, ip: str) -> dict:
        for d in self.list_devices():
            if d["ip"] == ip:
                d["finding_details"] = [self._finding_dict(f) for f in self.a.prioritized() if f.ip == ip]
                return d
        return {"error": f"no device with IP {ip} in this scan"}

    def list_findings(self) -> list[dict]:
        return [self._finding_dict(f) for f in self.a.prioritized()]

    def compare_with_previous(self) -> dict:
        if not self.prev:
            return {"available": False}
        return {"available": True, **compare(self.prev, self.a)}


def fallback_answer(tools: ScanTools) -> str:
    """Deterministic built-in answer, short and simple: the most useful facts for any question."""
    s = tools.get_summary()
    ro = tools.lang == "ro"
    lines = [
        "Asistentul online nu răspunde acum. Pe scurt:" if ro else "The online assistant is not answering right now. In short:",
        (f"Scorul casei tale: {s['standard_score']} din 100 ({s['band'].lower()})." if ro
         else f"Your home's score: {s['standard_score']} out of 100 ({s['band'].lower()})."),
    ]
    top = s["most_dangerous_device"]
    if top:
        name = top["type"] + (f" {top['vendor']}" if top["vendor"] else "")
        lines.append(f"Cea mai mare problemă e la {name} ({top['ip']})." if ro
                     else f"The biggest problem is on {name} ({top['ip']}).")
    ff = s["first_fix"]
    if ff:
        lines.append(("Problema: " if ro else "The problem: ") + ff["title"].rstrip(".") + ".")
        lines.append("Ce faci:" if ro else "What to do:")
        lines.extend(f"{i}. {step}" for i, step in enumerate(ff["fix_steps"][:3], 1))
    else:
        lines.append("Nu am găsit nimic de reparat." if ro else "We found nothing to fix.")
    ch = tools.compare_with_previous()
    if ch.get("available"):
        fixed = len(ch["resolved_findings"])
        if ro:
            more = f" și ai reparat {fixed} {'lucru' if fixed == 1 else 'lucruri'}." if fixed else "."
            lines.append(f"Față de verificarea de dinainte, scorul a trecut de la {ch['score_before']} la {ch['score_after']}" + more)
        else:
            more = f" and you fixed {fixed} {'thing' if fixed == 1 else 'things'}." if fixed else "."
            lines.append(f"Since the previous check, the score went from {ch['score_before']} to {ch['score_after']}" + more)
    return "\n".join(lines)


def voice_fallback(tools: ScanTools) -> str:
    """Built-in answer for voice mode: 2-3 spoken sentences, no addresses or numbers."""
    s = tools.get_summary()
    ro = tools.lang == "ro"
    n = s["standard_score"]
    pts = "un punct" if n == 1 else (f"{n} de puncte" if n % 100 >= 20 or n % 100 == 0 and n else f"{n} puncte")
    out = [f"Casa ta are {pts} din 100." if ro else f"Your home scores {n} out of 100."]
    top, ff = s["most_dangerous_device"], s["first_fix"]
    if top and ff:
        name = top["type"].lower() + (f" {top['vendor']}" if top["vendor"] else "")
        out.append(f"Cea mai mare problemă e la {name}: {ff['title'][:1].lower() + ff['title'][1:].rstrip('.')}." if ro
                   else f"The biggest problem is on the {name}: {ff['title'][:1].lower() + ff['title'][1:].rstrip('.')}.")
        if ff["fix_steps"]:
            out.append(("Primul pas: " if ro else "First step: ") + ff["fix_steps"][0][:1].lower() + ff["fix_steps"][0][1:])
    else:
        out.append("Nu am găsit nimic de reparat." if ro else "We found nothing to fix.")
    return to_speech_text(" ".join(out), tools.lang)


def ask(question: str, analysis: Analysis, lang: str = "ro", previous: Optional[Analysis] = None,
        provider=None, history: Optional[list[dict]] = None, style: str = "text") -> Answer:
    """style="voice": the answer will be read aloud (short, warm, no addresses); see ai/voice.py."""
    lang = lang if lang in LANGS else "ro"
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    # answer in the language of the question, not of the page; a short "ok?" keeps the conversation's language
    earlier = [m["content"] for m in (history or []) if m.get("role") == "user"]
    if earlier:
        lang = detect_language(earlier[-1], default=lang)
    lang = detect_language(question, default=lang)
    tools = ScanTools(analysis, lang, previous)
    provider = provider or get_provider()

    voice = style == "voice"
    built_in = voice_fallback if voice else fallback_answer
    if not question:
        return Answer(built_in(tools), "fallback", "empty question")
    try:
        extra = {"style": "voice"} if voice else {}            # providers without voice support keep working
        text = provider.answer(question, analysis, lang, previous, history=history or None, **extra)
        check(text, analysis, previous)   # never trust the network: verify again locally
        if voice:
            text = to_speech_text(text, lang) or text
        return Answer(text, "ai", tools_used=[getattr(provider, "name", "?")])
    except GroundingError as e:
        return Answer(built_in(tools), "fallback", f"grounding: {e}")
    except LLMUnavailable as e:
        return Answer(built_in(tools), "fallback", str(e))


class Conversation:
    """A multi-turn chat about one scan. History stays in the app (the gateway keeps nothing).

    Only successful AI turns are remembered, so the history always alternates user/assistant.
    """

    MAX_TURNS = 6

    def __init__(self, analysis: Analysis, lang: str = "ro", previous: Optional[Analysis] = None, provider=None):
        self.analysis, self.lang, self.previous = analysis, lang, previous
        self.provider = provider or get_provider()
        self.history: list[dict] = []

    def ask(self, question: str) -> Answer:
        ans = ask(question, self.analysis, self.lang, self.previous, self.provider, self.history)
        if ans.source == "ai":
            self.history += [{"role": "user", "content": question.strip()[:MAX_QUESTION_CHARS]},
                             {"role": "assistant", "content": ans.text}]
            self.history = self.history[-2 * self.MAX_TURNS:]
        return ans

    def reset(self) -> None:
        self.history = []
