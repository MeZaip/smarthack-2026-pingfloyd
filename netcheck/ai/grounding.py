"""Grounding guard (NFR-06): reject any AI answer that mentions things the scan did not show."""
from __future__ import annotations

import re

from ..core.analysis import Analysis

_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_CVE = re.compile(r"\bCVE-\d{4}-\d{3,}\b", re.I)
_PORT_PATTERNS = [
    re.compile(r"\bport(?:ul|urile|uri|s)?\s*(?:nr\.?\s*)?(\d{1,5})\b", re.I),
    re.compile(r"\b(\d{1,5})\s*/\s*(?:tcp|udp)\b", re.I),
    re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}:(\d{1,5})\b"),
]
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_URL = re.compile(r"\bhttps?://([A-Za-z0-9][A-Za-z0-9.-]*)", re.I)


class GroundingError(Exception):
    pass


def evidence_sets(*analyses: Analysis) -> tuple[set[str], set[int], str]:
    ips: set[str] = set()
    ports: set[int] = set()
    text_parts: list[str] = []
    for a in analyses:
        if not (a and a.ok):
            continue
        for h in a.scan.hosts:
            ips.add(h.ip)
            for p in h.ports:
                ports.add(p.portid)
                text_parts.extend([p.product, p.version, p.extrainfo, *p.scripts.values()])
    return ips, ports, "\n".join(text_parts)


def check(answer: str, *analyses: Analysis) -> None:
    """Raise GroundingError with a short reason if the answer is not grounded."""
    ips, ports, raw = evidence_sets(*analyses)

    for ip in _IPV4.findall(answer):
        if ip not in ips:
            raise GroundingError(f"mentions IP {ip} not in scan")

    for pat in _PORT_PATTERNS:
        for m in pat.findall(answer):
            if int(m) not in ports:
                raise GroundingError(f"mentions port {m} not in scan")

    for cve in _CVE.findall(answer):
        if cve.lower() not in raw.lower():
            raise GroundingError(f"mentions {cve} not in scan")

    for host in _URL.findall(answer):
        if host not in ips:
            raise GroundingError(f"mentions external link {host}")

    for ph in _PHONE.findall(answer):
        digits = re.sub(r"\D", "", ph)
        if len(digits) >= 9 and not _IPV4.search(ph):
            raise GroundingError("mentions a phone-like number")
