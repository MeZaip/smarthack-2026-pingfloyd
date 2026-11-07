"""„Dovedește!" — re-check ONE finding (one IP:port) in a few seconds, after the user says it is fixed.

* TCP: nmap -sT (TCP connect) needs NO root, so the web UI stays unprivileged (NFR-04).
* UDP: needs root -> only from the terminal: `netcheck verify <ip> <port> --udp --confirm`.
* The target goes through the same guardrail as a full scan, and the answer through the same rules.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

from . import guardrail, history, netdetect
from .models import Finding, Host
from .parser import ScanFileError, parse_bytes
from .rules import classify_host

Runner = Callable[[list[str]], bytes]


@dataclass
class VerifyResult:
    status: str        # resolved | still_open | needs_root | unsupported | refused | error
    message_ro: str
    message_en: str
    evidence: str = ""

    def message(self, lang: str) -> str:
        return self.message_ro if lang == "ro" else self.message_en


def _default_runner(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True, timeout=90)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="replace")[:300])
    return proc.stdout


def build_command(ip: str, port: int, udp: bool) -> list[str]:
    scan = ["-sU"] if udp else ["-sT"]
    cmd = ["nmap", *scan, "-Pn", "-n", "-sV", "--version-light", "--script", "http-title",
           "-p", str(port), "--max-rate", "100", "-oX", "-", ip]
    if udp and os.name != "nt" and os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    return cmd


def verify(finding: Finding, original_host: Host | None = None, *, scan_id: int | None = None,
           device_id: str = "", allowlist: list | None = None, allow_udp: bool = False,
           runner: Runner | None = None, save: bool = True) -> VerifyResult:
    if finding.port is None:
        return VerifyResult("unsupported",
                            "Pentru un dispozitiv necunoscut nu există un singur port de verificat. "
                            "Dă-i un nume pe hartă sau deconectează-l, apoi fă o scanare completă.",
                            "An unknown device has no single port to re-check. Name it on the map or "
                            "disconnect it, then run a full scan.")
    udp = finding.protocol == "udp"
    if udp and not allow_udp:
        cmd = f"netcheck verify {finding.ip} {finding.port} --udp --confirm"
        return VerifyResult("needs_root",
                            f"Porturile UDP se verifică doar din terminal (au nevoie de drepturi de administrator): {cmd}",
                            f"UDP ports can only be re-checked from the terminal (admin rights needed): {cmd}")
    try:
        if allowlist is None:
            allowlist = guardrail.build_allowlist(netdetect.detect().subnet)
        guardrail.check_target(finding.ip, allowlist, confirmed=True)
    except (guardrail.ScopeError, netdetect.NetworkDetectError) as e:
        return VerifyResult("refused", f"⛔ {e}", f"⛔ {e}")
    if runner is None:
        if not shutil.which("nmap"):
            return VerifyResult("error", "nmap nu este instalat (brew install nmap).",
                                "nmap is not installed (brew install nmap).")
        runner = _default_runner
    try:
        hosts = parse_bytes(runner(build_command(finding.ip, finding.port, udp)))
    except (ScanFileError, RuntimeError, subprocess.TimeoutExpired, OSError) as e:
        return VerifyResult("error", f"Verificarea a eșuat: {e}", f"The re-check failed: {e}")

    seen = next((h for h in hosts if h.ip == finding.ip), None)
    ports = [p for p in (seen.ports if seen else []) if p.portid == finding.port and p.protocol == finding.protocol]
    # keep the identity from the full scan (a connect scan cannot see MAC vendors)
    probe = Host(ip=finding.ip, vendor=original_host.vendor if original_host else "x",
                 hostname=original_host.hostname if original_host else "x", ports=ports)
    still = [f for f in classify_host(finding.file, probe) if f.code == finding.code and f.port == finding.port]
    evidence = "; ".join(f"{p.portid}/{p.protocol} {p.state} {p.service}" for p in ports) or "port not reported (closed)"
    if still:
        res = VerifyResult("still_open",
                           "Încă deschis: problema se vede în continuare. Mai încearcă pașii sau cere ajutor.",
                           "Still open: the problem is still visible. Try the steps again or ask for help.", evidence)
    else:
        res = VerifyResult("resolved", "✔ Dovedit: ușa e închisă!", "✔ Proven: the door is closed!", evidence)
    if save:
        history.add_verification(scan_id, device_id, finding.ip, finding.port, finding.code, res.status, evidence)
    return res


def estimated_score(score: int, findings: list[Finding], verifications: dict) -> int:
    """Clearly-labelled ESTIMATE: standard score + points of findings proven fixed since the scan."""
    gained = sum(f.points for f in findings
                 if verifications.get((f.ip, f.port, f.code), {}).get("status") == "resolved")
    return min(100, score + gained)
