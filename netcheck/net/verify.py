"""„Dovedește!" — re-check ONE finding (one IP:port) in seconds, after the user says it is fixed.

* TCP: `nmap -sT` (TCP connect) needs NO root (NFR-04).
* UDP: needs root -> only with --udp, nmap then runs through sudo.
* Same guardrail as a full scan; the answer goes through the same rules (core.rules).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable

from ..core.models import Finding, Host
from ..core.parser import ScanFileError, parse_bytes
from ..core.rules import evaluate_host
from . import guardrail

Runner = Callable[[list[str]], bytes]


@dataclass
class VerifyResult:
    status: str        # resolved | still_open | needs_root | unsupported | refused | error
    en: str
    ro: str
    evidence: str = ""
    still: list[str] = field(default_factory=list)

    def message(self, lang: str = "en") -> str:
        return self.ro if lang == "ro" else self.en


def _default_runner(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="replace")[:300])
    return proc.stdout


def build_command(ip: str, port: int, udp: bool) -> list[str]:
    cmd = ["nmap", "-sU" if udp else "-sT", "-Pn", "-n", "-sV", "--version-light", "--script", "http-title",
           "-p", str(port), "--max-rate", "100", "-oX", "-", ip]
    if udp and os.name != "nt" and os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    return cmd


def verify(finding: Finding, original: Host | None, allowlist: list, *, allow_udp: bool = False,
           runner: Runner | None = None) -> VerifyResult:
    if finding.port is None:
        return VerifyResult("unsupported",
                            "An unknown device has no single port to re-check: identify or disconnect it, then run a full scan.",
                            "Un dispozitiv necunoscut nu are un singur port de verificat: identifică-l sau deconectează-l, "
                            "apoi fă o scanare completă.")
    udp = finding.protocol == "udp"
    if udp and not allow_udp:
        cmd = f"netcheck verify <scan.xml> {finding.ip} {finding.port} --udp --confirm"
        return VerifyResult("needs_root", f"UDP ports need admin rights: {cmd}",
                            f"Porturile UDP au nevoie de drepturi de administrator: {cmd}")
    try:
        guardrail.check_target(finding.ip, allowlist, confirmed=True)
    except guardrail.ScopeError as e:
        return VerifyResult("refused", f"⛔ {e.en}", f"⛔ {e.ro}")
    if runner is None:
        if not shutil.which("nmap"):
            return VerifyResult("error", "nmap is not installed (brew install nmap).",
                                "nmap nu este instalat (brew install nmap).")
        runner = _default_runner
    try:
        scan = parse_bytes(runner(build_command(finding.ip, finding.port, udp)), source="verify")
    except (ScanFileError, RuntimeError, subprocess.TimeoutExpired, OSError) as e:
        return VerifyResult("error", f"The re-check failed: {e}", f"Verificarea a eșuat: {e}")

    seen = next((h for h in scan.hosts if h.ip == finding.ip), None)
    ports = [p for p in (seen.ports if seen else [])
             if p.portid == finding.port and p.protocol == finding.protocol]
    # keep the identity from the full scan: a connect scan cannot see MAC vendors
    probe = Host(ip=finding.ip, status="up",
                 vendor=(original.vendor if original else None) or "?",
                 hostnames=(original.hostnames if original else None) or ["?"], ports=ports)
    still = [f.code for f in evaluate_host(probe) if f.code == finding.code and f.port == finding.port]
    evidence = "; ".join(f"{p.portid}/{p.protocol} {p.state} {p.service}" for p in ports) or "port not reported (closed)"
    if still:
        return VerifyResult("still_open", "Still open: the problem is still visible.",
                            "Încă deschis: problema se vede în continuare.", evidence, still)
    return VerifyResult("resolved", "✔ Proven: the door is closed!", "✔ Dovedit: ușa e închisă!", evidence)
