"""Live scans only: real device names that nmap discovers beyond reverse DNS.

Phone hotspots give no DNS names, and modern phones/PCs use private (random) MAC addresses, so
without this almost every device in a hotspot lab looks like an UNKNOWN_DEVICE. Two standard,
read-only nmap scripts ask the device for its own name:
  * nbstat                - a Windows PC answers with its computer name (NetBIOS), e.g. DESKTOP-AB12
  * dns-service-discovery - Apple and many IoT devices announce "<name>.local" over mDNS
A name found this way is a hostname in the sense of the catalog ("no MAC vendor and no hostname").

File analysis (Validation/Test Set, `netcheck analyze`) never uses this: those files are plain
`nmap -sS -sU -sV` output and are judged exactly as given.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as _stdlib_et

from ..core.parser import ScanFileError, parse_bytes

try:
    from defusedxml import ElementTree as _safe_et  # type: ignore
except ImportError:  # pragma: no cover
    _safe_et = None

LIVE_SCRIPTS = ["nbstat", "dns-service-discovery"]

_NETBIOS = re.compile(r"NetBIOS name:\s*([A-Za-z0-9][A-Za-z0-9_.-]{0,62})")
_MDNS = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9-]{0,62})\.local\b")
_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")


def _root(data: bytes):
    parse_bytes(data)            # same safety checks as every scan file (no DTD tricks, size limit)
    if _safe_et is not None:
        return _safe_et.fromstring(data, forbid_dtd=False, forbid_entities=True, forbid_external=True)
    return _stdlib_et.fromstring(data)


def discovered_names(data: bytes) -> dict[str, str]:
    """{ip: name} from nbstat (host script) and mDNS (port 5353 script). Hostile text is filtered."""
    try:
        root = _root(data)
    except (ScanFileError, _stdlib_et.ParseError, ValueError):
        return {}
    names: dict[str, str] = {}
    for host in root.findall("host"):
        ip = next((a.get("addr") for a in host.findall("address") if a.get("addrtype") in ("ipv4", "ipv6")), None)
        if not ip:
            continue
        found = None
        for sc in host.findall("hostscript/script"):
            if sc.get("id") == "nbstat":
                m = _NETBIOS.search(sc.get("output") or "")
                if m and m.group(1) != "<unknown>":
                    found = m.group(1)
        if not found:
            for sc in host.findall("ports/port/script"):
                if sc.get("id") == "dns-service-discovery":
                    m = _MDNS.search(sc.get("output") or "")
                    if m:
                        found = m.group(1)
        if found and _SAFE.match(found):
            names[ip] = found
    return names


def live_command(cmd: list[str]) -> list[str]:
    """Add the name-discovery scripts to the --script list of a live scan command."""
    cmd = list(cmd)
    if "--script" in cmd:
        i = cmd.index("--script") + 1
        scripts = [s for s in cmd[i].split(",") if s]
        cmd[i] = ",".join(scripts + [s for s in LIVE_SCRIPTS if s not in scripts])
    else:
        cmd[-1:-1] = ["--script", ",".join(LIVE_SCRIPTS)]
    return cmd


def is_private_mac(mac: str | None) -> bool:
    """Locally administered (random / 'private Wi-Fi address') MACs have bit 1 of the first byte set."""
    try:
        return bool(int((mac or "").replace("-", ":").split(":")[0], 16) & 0x02)
    except ValueError:
        return False
