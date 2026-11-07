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
from .providers import LLMUnavailable, get_provider

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
    """Deterministic built-in answer: the most useful facts for any question."""
    s = tools.get_summary()
    ro = tools.lang == "ro"
    lines = [
        ("Asistentul AI nu este disponibil acum. Iată rezumatul scanării:" if ro
         else "The AI assistant is not available right now. Here is the scan summary:"),
        (f"Scor rețea: {s['standard_score']}/100 ({s['band']})." if ro
         else f"Network score: {s['standard_score']}/100 ({s['band']})."),
    ]
    top = s["most_dangerous_device"]
    if top:
        name = top["hostname"] or top["vendor"] or top["type"]
        lines.append((f"Cel mai periculos dispozitiv: {top['ip']} ({name})." if ro
                      else f"Most dangerous device: {top['ip']} ({name})."))
    ff = s["first_fix"]
    if ff:
        lines.append(("Primul pas: " if ro else "First step: ") + ff["title"] + ".")
        lines.extend(f"{i}. {step}" for i, step in enumerate(ff["fix_steps"][:3], 1))
    else:
        lines.append("Nu am găsit probleme în această scanare." if ro else "No problems were found in this scan.")
    ch = tools.compare_with_previous()
    if ch.get("available"):
        lines.append(
            (f"Față de scanarea anterioară: scor {ch['score_before']} → {ch['score_after']}, "
             f"{len(ch['resolved_findings'])} probleme rezolvate, {len(ch['new_findings'])} noi, "
             f"{len(ch['new_devices'])} dispozitive noi." if ro else
             f"Compared with the previous scan: score {ch['score_before']} → {ch['score_after']}, "
             f"{len(ch['resolved_findings'])} problems resolved, {len(ch['new_findings'])} new, "
             f"{len(ch['new_devices'])} new devices."))
    return "\n".join(lines)


def ask(question: str, analysis: Analysis, lang: str = "ro", previous: Optional[Analysis] = None,
        provider=None, history: Optional[list[dict]] = None) -> Answer:
    lang = lang if lang in LANGS else "ro"
    tools = ScanTools(analysis, lang, previous)
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    provider = provider or get_provider()

    if not question:
        return Answer(fallback_answer(tools), "fallback", "empty question")
    try:
        text = provider.answer(question, analysis, lang, previous, history=history or None)
        check(text, analysis, previous)   # never trust the network: verify again locally
        return Answer(text, "ai", tools_used=[getattr(provider, "name", "?")])
    except GroundingError as e:
        return Answer(fallback_answer(tools), "fallback", f"grounding: {e}")
    except LLMUnavailable as e:
        return Answer(fallback_answer(tools), "fallback", str(e))


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
