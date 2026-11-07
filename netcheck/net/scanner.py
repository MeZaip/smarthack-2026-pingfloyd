"""Live scan (FR-04). Only this step needs root (NFR-04): nmap runs through sudo,
our own Python process stays unprivileged. Output is nmap XML, the same format as the test data."""
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


_NMAP_WINDOWS = [r"C:\Program Files (x86)\Nmap\nmap.exe", r"C:\Program Files\Nmap\nmap.exe"]


class ScanError(Exception):
    pass


def find_nmap() -> str | None:
    """Full path to nmap: PATH first, then the default Windows install folders (the installer
    does not always add itself to PATH)."""
    found = shutil.which("nmap")
    if found:
        return found
    for p in _NMAP_WINDOWS if os.name == "nt" else []:
        if os.path.exists(p):
            return p
    return None


def _services_candidates() -> list[str]:
    found = []
    nmap = find_nmap()
    if nmap:
        here = Path(os.path.realpath(nmap)).parent
        found += [str(here / "nmap-services"), str(here.parent / "share" / "nmap" / "nmap-services")]
    return found + [p for p in _SERVICES_PATHS if p not in found]


def top_tcp_ports(n: int = 1000, paths: list[str] | None = None) -> str:
    """Exactly nmap's own top-N TCP ports (by frequency in nmap-services).

    The file is looked up next to the nmap binary actually used (custom install
    folders included), then in the usual install locations."""
    for p in paths or _services_candidates():
        if not os.path.exists(p):
            continue
        rows = []
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.split()
                if line.startswith("#") or len(parts) < 3 or not parts[1].endswith("/tcp"):
                    continue
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
        "--script", "http-title",            # rule HTTP_ADMIN_CLEARTEXT needs the page title
        "-p", f"T:{top_tcp_ports()},U:{UDP_PORTS}",
        "--max-rate", str(MAX_RATE),
        "--host-timeout", "120s",
        "-oX", str(out_xml),
        target,
    ]


def run_scan(target: str, out_dir: str | os.PathLike = "scans") -> Path:
    """target MUST already be validated by guardrail.check_target()."""
    nmap = find_nmap()
    if not nmap:
        raise ScanError("nmap is not installed (Windows: https://nmap.org/download, macOS: brew install nmap)")
    if os.name == "nt":
        from .elevate import is_admin
        if not is_admin():
            raise ScanError("on Windows a terminal scan needs an administrator terminal "
                            "(or use the \"Check my network\" button in the app, which asks for permission)")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_xml = out_dir / f"scan_{datetime.now():%Y%m%d_%H%M%S}.xml"
    cmd = build_command(target, out_xml)
    cmd[0] = nmap  # full path: the Windows installer does not always put nmap on PATH
    if os.name != "nt" and os.geteuid() != 0:
        cmd = ["sudo"] + cmd  # privilege only for the packet-level scan
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_xml.exists():
        raise ScanError(f"nmap failed: {proc.stderr.strip()[:300]}")
    return out_xml
