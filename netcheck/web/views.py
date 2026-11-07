"""View models: turn core.analysis.Analysis + explain texts into what the Jinja templates show.

The web layer only reads; findings, severities and scores come unchanged from the Rule Engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..core.analysis import Analysis
from ..core.device import DEVICE_LABELS
from ..core.models import Finding
from ..explain.texts import SEVERITY_LABELS, score_band, text_for

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


class Explain:
    """Template helper `ex`: built-in, human-reviewed RO/EN texts (never the LLM)."""
    SEVERITY_ICON = {k: v["icon"] for k, v in SEVERITY_LABELS.items()}
    SEVERITY_LABEL = {lang: {k: v[lang] for k, v in SEVERITY_LABELS.items()} for lang in ("ro", "en")}

    @staticmethod
    def get(code: str, lang: str = "ro") -> dict:
        try:
            return text_for(code, lang)
        except KeyError:
            return {"title": code, "explain": "", "steps": [], "refs": []}

    @staticmethod
    def score_band(score: Optional[int], lang: str = "ro") -> tuple[str, str, str]:
        """(css class, icon, label): colour is never the only signal (NFR-08)."""
        if score is None:
            return ("err", "✖", "Fișier ilizibil" if lang == "ro" else "Unreadable file")
        b = score_band(score, lang)
        return ({"green": "good", "amber": "warn", "red": "bad"}[b["color"]], b["icon"], b["label"])


@dataclass
class DeviceView:
    ip: str
    hostname: Optional[str]
    vendor: Optional[str]
    type_guess: str
    type_label: str
    mac_masked: Optional[str]
    open_ports: list[dict]
    risk_points: int

    @property
    def name(self) -> str:
        return self.hostname or self.vendor or self.type_label


@dataclass
class ScanView:
    file: str
    ok: bool
    error: Optional[str] = None
    score: Optional[int] = None
    devices: list[DeviceView] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)   # prioritized: worst first

    @property
    def most_dangerous(self) -> Optional[DeviceView]:
        risky = [d for d in self.devices if d.risk_points > 0]
        return max(risky, key=lambda d: d.risk_points) if risky else None

    @property
    def first_fix(self) -> Optional[Finding]:
        dev = self.most_dangerous
        mine = [f for f in self.findings if dev and f.ip == dev.ip]
        return mine[0] if mine else None


def scan_view(a: Analysis, lang: str) -> ScanView:
    if not a.ok:
        return ScanView(file=a.file, ok=False, error=a.error)
    devices = [DeviceView(
        ip=d["ip"], hostname=d["hostname"], vendor=d["vendor"], type_guess=d["type"],
        type_label=DEVICE_LABELS.get(d["type"], DEVICE_LABELS["unknown"])[lang],
        mac_masked=d["mac"], risk_points=d["risk_points"],
        open_ports=sorted(d["open_ports"], key=lambda p: (p["protocol"], p["port"])),
    ) for d in a.devices()]   # already sorted: most risk first
    return ScanView(file=a.file, ok=True, score=a.score, devices=devices, findings=a.prioritized())


def alerts(changes: Optional[dict], lang: str) -> list[str]:
    """FR-13: new device / newly opened port since the previous scan (secure replacements excluded)."""
    if not changes:
        return []
    ro = lang == "ro"
    out = [("Dispozitiv nou în rețea: " if ro else "New device on the network: ") + ip
           for ip in changes["new_devices"]]
    out += [("Port nou deschis: " if ro else "Newly opened port: ")
            + f"{p['ip']} {p['port']}/{p['protocol']} ({p['service'] or '?'})"
            for p in changes["new_port_alerts"]]
    return out
