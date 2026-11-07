"""Live scan (FR-04). Only this step needs root (NFR-04): nmap is run through sudo,
our own Python process stays unprivileged. Output is saved as nmap XML."""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

UDP_PORTS = "53,123,161,1900,5353"
MAX_RATE = 100  # packets/second (rules of engagement)
_SERVICES_PATHS = [
    "/opt/homebrew/share/nmap/nmap-services",
    "/usr/local/share/nmap/nmap-services",
    "/usr/share/nmap/nmap-services",
    r"C:\Program Files (x86)\Nmap\nmap-services",
    r"C:\Program Files\Nmap\nmap-services",
]


class ScanError(Exception):
    pass


def top_tcp_ports(n: int = 1000) -> str:
    """Read nmap's own frequency table to get exactly the top-N TCP ports."""
    for p in _SERVICES_PATHS:
        if os.path.exists(p):
            rows = []
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) >= 3 and parts[1].endswith("/tcp"):
                        try:
                            rows.append((float(parts[2]), int(parts[1].split("/")[0])))
                        except ValueError:
                            pass
            ports = sorted({port for _, port in sorted(rows, reverse=True)[:n]})
            if ports:
                return ",".join(map(str, ports))
    return "1-10000"  # superset fallback


def build_command(target: str, out_xml: Path) -> list[str]:
    return [
        "nmap", "-sS", "-sU", "-sV", "--version-light",
        "--script", "http-title",
        "-p", f"T:{top_tcp_ports()},U:{UDP_PORTS}",
        "--max-rate", str(MAX_RATE),
        "--host-timeout", "120s",
        "-oX", str(out_xml),
        target,
    ]


def run_scan(target: str, out_dir: str | os.PathLike = "scans") -> Path:
    """target MUST already be validated by guardrail.check_target()."""
    if not shutil.which("nmap"):
        raise ScanError("nmap is not installed (macOS: brew install nmap)")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_xml = out_dir / f"scan_{datetime.now():%Y%m%d_%H%M%S}.xml"
    cmd = build_command(target, out_xml)
    if os.name != "nt" and os.geteuid() != 0:
        cmd = ["sudo"] + cmd  # privilege only for the packet-level scan
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_xml.exists():
        raise ScanError(f"nmap failed: {proc.stderr.strip()[:300]}")
    return out_xml
