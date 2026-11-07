"""Official finding catalog and detection rules (FR-06).

Pure, deterministic functions: same ScanResult -> same findings (NFR-05).
No LLM is involved anywhere in this module.

Assumptions (to confirm with mentors; flip the constants below if needed):
  * only ports with state exactly "open" count ("open|filtered" does not)
  * HTTP_ADMIN_CLEARTEXT requires service name exactly "http"
  * Samba version ranges such as "3.X - 4.X" are judged by the upper bound
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from .models import Finding, Host, Port, ScanResult


@dataclass(frozen=True)
class CatalogEntry:
    code: str
    severity: str
    points: int


CATALOG: dict[str, CatalogEntry] = {e.code: e for e in [
    CatalogEntry("TELNET_OPEN", "high", 20),
    CatalogEntry("RDP_EXPOSED", "high", 20),
    CatalogEntry("VNC_EXPOSED", "high", 20),
    CatalogEntry("DB_EXPOSED", "high", 20),
    CatalogEntry("CAMERA_STREAM_EXPOSED", "high", 20),
    CatalogEntry("OUTDATED_SERVICE", "high", 20),
    CatalogEntry("FTP_CLEARTEXT", "medium", 10),
    CatalogEntry("HTTP_ADMIN_CLEARTEXT", "medium", 10),
    CatalogEntry("SMB_EXPOSED", "medium", 10),
    CatalogEntry("MQTT_EXPOSED", "medium", 10),
    CatalogEntry("UPNP_EXPOSED", "medium", 10),
    CatalogEntry("SNMP_EXPOSED", "medium", 10),
    CatalogEntry("PRINTER_RAW_EXPOSED", "low", 5),
    CatalogEntry("UNKNOWN_DEVICE", "low", 5),
    CatalogEntry("SSH_OPEN", "info", 0),
]}

SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1, "info": 0}

# simple "service name -> code" rules (any protocol)
SERVICE_CODES: dict[str, str] = {
    "telnet": "TELNET_OPEN",
    "ms-wbt-server": "RDP_EXPOSED",
    "vnc": "VNC_EXPOSED",
    "mysql": "DB_EXPOSED",
    "postgresql": "DB_EXPOSED",
    "redis": "DB_EXPOSED",
    "mongodb": "DB_EXPOSED",
    "rtsp": "CAMERA_STREAM_EXPOSED",
    "ftp": "FTP_CLEARTEXT",
    "mqtt": "MQTT_EXPOSED",
    "jetdirect": "PRINTER_RAW_EXPOSED",
    "ssh": "SSH_OPEN",
}
UDP_ONLY_CODES: dict[str, str] = {
    "upnp": "UPNP_EXPOSED",
    "snmp": "SNMP_EXPOSED",
}
SMB_SERVICES = ("microsoft-ds", "netbios-ssn")
HTTP_SERVICES = ("http",)
ADMIN_TITLE_WORDS = ("login", "admin", "config", "setup", "router", "settings")


# ---------------------------------------------------------------- versions
_NUM = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def _version_tuple(text: str) -> Optional[tuple[int, int, int]]:
    m = _NUM.search(text or "")
    if not m:
        return None
    return tuple(int(g) if g else 0 for g in m.groups())  # type: ignore[return-value]


def _samba_upper(version: str) -> Optional[int]:
    """'3.6.25' -> 3 ; '3.X - 4.X' -> 4 ; '4.6.2' -> 4."""
    majors = re.findall(r"(\d+)\.(?:\d+|[xX])", version or "")
    if not majors:
        v = _version_tuple(version)
        return v[0] if v else None
    return max(int(m) for m in majors)


def outdated_reason(port: Port) -> Optional[str]:
    """Return a short reason if (product, version) is on the official outdated list."""
    product = (port.product or "").lower()
    version = port.version or ""
    if not product or not version:
        return None
    v = _version_tuple(version)
    if "vsftpd" in product:
        if version.strip().startswith("2.3.4"):
            return "vsftpd 2.3.4"
        return None
    if "openssh" in product:
        if v and (v[0], v[1]) < (7, 4):
            return f"OpenSSH {version} (< 7.4)"
        return None
    if "apache" in product and "httpd" in product:
        if v and (v[0], v[1]) <= (2, 2):
            return f"Apache httpd {version} (2.2.x or older)"
        return None
    if "iis" in product:
        if v and (v[0], v[1]) <= (7, 5):
            return f"Microsoft IIS {version} (7.5 or older)"
        return None
    if "samba" in product:
        upper = _samba_upper(version)
        if upper is not None and upper <= 3:
            return f"Samba {version} (3.x or older)"
        return None
    return None


# ---------------------------------------------------------------- helpers
def _describe(port: Port) -> str:
    parts = [f"{port.portid}/{port.protocol} open", f"service={port.service or '?'}"]
    pv = " ".join(x for x in (port.product, port.version) if x)
    if pv:
        parts.append(f"software={pv}")
    if port.tunnel:
        parts.append(f"tunnel={port.tunnel}")
    return ", ".join(parts)


def _finding(host: Host, port: Optional[Port], code: str, evidence: str) -> Finding:
    entry = CATALOG[code]
    return Finding(
        ip=host.ip,
        port=port.portid if port else None,
        protocol=port.protocol if port else None,
        code=code,
        severity=entry.severity,
        points=entry.points,
        evidence=evidence,
    )


def is_admin_http(port: Port) -> bool:
    if port.service not in HTTP_SERVICES or port.tunnel == "ssl":
        return False
    title = port.http_title.lower()
    return any(w in title for w in ADMIN_TITLE_WORDS)


# ---------------------------------------------------------------- per host
def evaluate_host(host: Host) -> list[Finding]:
    if host.status != "up":
        return []
    out: list[Finding] = []
    open_ports = host.open_ports

    for port in open_ports:
        svc = port.service
        code = SERVICE_CODES.get(svc)
        if code:
            out.append(_finding(host, port, code, _describe(port)))
        if port.protocol == "udp" and svc in UDP_ONLY_CODES:
            out.append(_finding(host, port, UDP_ONLY_CODES[svc], _describe(port)))
        if is_admin_http(port):
            out.append(_finding(host, port, "HTTP_ADMIN_CLEARTEXT",
                                f"{_describe(port)}, page title=\"{port.http_title}\""))
        reason = outdated_reason(port)
        if reason:
            out.append(_finding(host, port, "OUTDATED_SERVICE", f"{_describe(port)}; outdated: {reason}"))

    # SMB: one finding per device, port 445 if open else 139 (else first SMB port)
    smb_ports = [p for p in open_ports if p.service in SMB_SERVICES]
    if smb_ports:
        chosen = next((p for p in smb_ports if p.portid == 445), None) \
            or next((p for p in smb_ports if p.portid == 139), None) \
            or sorted(smb_ports, key=lambda p: p.portid)[0]
        out.append(_finding(host, chosen, "SMB_EXPOSED", _describe(chosen)))

    # UNKNOWN_DEVICE: no MAC vendor, no hostname, at least one open port
    if not host.vendor and not host.hostnames and open_ports:
        out.append(_finding(host, None, "UNKNOWN_DEVICE",
                            f"no MAC vendor, no hostname, {len(open_ports)} open port(s)"))
    return out


def evaluate(scan: ScanResult) -> list[Finding]:
    seen = set()
    findings: list[Finding] = []
    for host in scan.hosts:
        for f in evaluate_host(host):
            key = (f.ip, f.port, f.code)
            if key in seen:
                continue
            seen.add(key)
            findings.append(f)
    findings.sort(key=lambda f: f.sort_key)
    return findings


def network_score(findings: list[Finding]) -> int:
    """Official standard score (FR-09)."""
    return max(0, 100 - sum(f.points for f in findings))


def device_risk(findings: list[Finding]) -> dict[str, int]:
    """Sum of points per IP - used to pick 'the most dangerous device'."""
    risk: dict[str, int] = {}
    for f in findings:
        risk[f.ip] = risk.get(f.ip, 0) + f.points
    return risk


def prioritized(findings: list[Finding]) -> list[Finding]:
    """Highest risk first, deterministic tie-break."""
    return sorted(findings, key=lambda f: (-SEVERITY_RANK[f.severity], -f.points, f.sort_key))
