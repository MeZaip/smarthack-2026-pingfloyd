"""Official finding catalog + detection rules (FR-06). Deterministic, no LLM.

Rules are applied LITERALLY as written in the brief:
  * only ports in state "open" count ("open|filtered" and "filtered" do not)
  * decisions use the service NAME nmap reported, never the port number
"""
from __future__ import annotations

import ipaddress
import re

from .models import Finding, Host, Port

# code -> (severity, points)
CATALOG: dict[str, tuple[str, int]] = {
    "TELNET_OPEN": ("high", 20),
    "RDP_EXPOSED": ("high", 20),
    "VNC_EXPOSED": ("high", 20),
    "DB_EXPOSED": ("high", 20),
    "CAMERA_STREAM_EXPOSED": ("high", 20),
    "OUTDATED_SERVICE": ("high", 20),
    "FTP_CLEARTEXT": ("medium", 10),
    "HTTP_ADMIN_CLEARTEXT": ("medium", 10),
    "SMB_EXPOSED": ("medium", 10),
    "MQTT_EXPOSED": ("medium", 10),
    "UPNP_EXPOSED": ("medium", 10),
    "SNMP_EXPOSED": ("medium", 10),
    "PRINTER_RAW_EXPOSED": ("low", 5),
    "UNKNOWN_DEVICE": ("low", 5),
    "SSH_OPEN": ("info", 0),
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}

# service name -> code (any protocol)
SIMPLE_SERVICE_RULES: dict[str, str] = {
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
# service name -> code, only when protocol is UDP
UDP_SERVICE_RULES: dict[str, str] = {
    "upnp": "UPNP_EXPOSED",
    "snmp": "SNMP_EXPOSED",
}
SMB_SERVICES = {"microsoft-ds", "netbios-ssn"}
ADMIN_TITLE_WORDS = ("login", "admin", "config", "setup", "router", "settings")


def _ver_tuple(version: str) -> tuple[int, ...] | None:
    """'7.2p2 Ubuntu 4' -> (7, 2); '2.2.34' -> (2, 2, 34); '3.X - 4.X' -> (3,)."""
    m = re.match(r"\s*(\d+(?:\.\d+)*)", version or "")
    if not m:
        return None
    return tuple(int(x) for x in m.group(1).split("."))


def outdated_reason(port: Port) -> str | None:
    """Return a short reason if product/version is on the official outdated list."""
    prod = port.product.lower()
    v = _ver_tuple(port.version)
    if v is None:
        return None
    if "vsftpd" in prod and port.version.strip().startswith("2.3.4"):
        return "vsftpd 2.3.4"
    if "openssh" in prod and v[:2] < (7, 4):
        return f"OpenSSH {port.version} (< 7.4)"
    if "apache" in prod and "httpd" in prod and v[:2] <= (2, 2):
        return f"Apache httpd {port.version} (<= 2.2.x)"
    if "iis" in prod and v[:2] <= (7, 5):
        return f"Microsoft IIS {port.version} (<= 7.5)"
    if "samba" in prod and v[0] <= 3:
        return f"Samba {port.version} (<= 3.x)"
    return None


def is_http_admin_cleartext(port: Port) -> bool:
    if port.service != "http" or port.tunnel == "ssl":
        return False
    title = port.title.lower()
    return any(w in title for w in ADMIN_TITLE_WORDS)


def _mk(file: str, host: Host, port: Port | None, code: str, evidence: str) -> Finding:
    sev, pts = CATALOG[code]
    return Finding(
        file=file,
        ip=host.ip,
        port=port.portid if port else None,
        code=code,
        severity=sev,
        points=pts,
        protocol=port.protocol if port else "",
        service=port.service if port else "",
        product=port.product if port else "",
        version=port.version if port else "",
        evidence=evidence,
    )


def _port_evidence(port: Port) -> str:
    parts = [f"{port.portid}/{port.protocol} open", f"service={port.service or '?'}"]
    if port.product:
        parts.append(f"product={port.product} {port.version}".strip())
    if port.tunnel:
        parts.append(f"tunnel={port.tunnel}")
    if port.title:
        parts.append(f'title="{port.title}"')
    return ", ".join(parts)


def classify_host(file: str, host: Host) -> list[Finding]:
    found: dict[tuple, Finding] = {}

    def add(f: Finding) -> None:
        found.setdefault((f.ip, f.port, f.code), f)

    open_ports = host.open_ports

    # SMB: one finding per device, port 445 if open else 139
    smb_ports = [p for p in open_ports if p.service in SMB_SERVICES]
    smb_chosen: Port | None = None
    if smb_ports:
        by_num = {p.portid: p for p in smb_ports}
        smb_chosen = by_num.get(445) or by_num.get(139) or sorted(smb_ports, key=lambda p: p.portid)[0]
        add(_mk(file, host, smb_chosen, "SMB_EXPOSED", _port_evidence(smb_chosen)))

    for p in open_ports:
        code = SIMPLE_SERVICE_RULES.get(p.service)
        if code:
            add(_mk(file, host, p, code, _port_evidence(p)))
        if p.protocol == "udp" and p.service in UDP_SERVICE_RULES:
            add(_mk(file, host, p, UDP_SERVICE_RULES[p.service], _port_evidence(p)))
        if is_http_admin_cleartext(p):
            add(_mk(file, host, p, "HTTP_ADMIN_CLEARTEXT", _port_evidence(p)))
        reason = outdated_reason(p)
        if reason:
            target = p
            # keep OUTDATED aligned with the single SMB finding of this device
            if p.service in SMB_SERVICES and smb_chosen is not None:
                target = smb_chosen
            add(_mk(file, host, target, "OUTDATED_SERVICE", f"{reason}; " + _port_evidence(p)))

    if open_ports and not host.vendor and not host.hostname:
        add(_mk(file, host, None, "UNKNOWN_DEVICE",
                f"no MAC vendor, no hostname, {len(open_ports)} open port(s)"))
    return list(found.values())


def _ip_key(ip: str):
    try:
        a = ipaddress.ip_address(ip)
        return (a.version, int(a))
    except ValueError:
        return (9, 0)


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (f.file, _ip_key(f.ip), -1 if f.port is None else f.port, f.code),
    )


def classify(file: str, hosts: list[Host]) -> list[Finding]:
    out: list[Finding] = []
    for h in hosts:
        out.extend(classify_host(file, h))
    return sort_findings(out)
