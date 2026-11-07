"""FR-01: find the active interface, its subnet and gateway with no manual input."""
from __future__ import annotations

import ipaddress
import platform
import re
import socket
import subprocess
from dataclasses import dataclass, asdict

import psutil


@dataclass
class NetworkInfo:
    interface: str
    ip: str
    netmask: str
    subnet: str        # e.g. "172.20.10.0/28"
    gateway: str

    def to_dict(self) -> dict:
        return asdict(self)


class NetworkDetectError(Exception):
    pass


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _default_route() -> tuple[str, str]:
    """Return (gateway, interface) of the default IPv4 route."""
    system = platform.system()
    if system == "Darwin":
        out = _run(["route", "-n", "get", "default"])
        gw = re.search(r"gateway:\s*(\S+)", out)
        iface = re.search(r"interface:\s*(\S+)", out)
        return (gw.group(1) if gw else "", iface.group(1) if iface else "")
    if system == "Linux":
        out = _run(["ip", "-4", "route", "show", "default"])
        m = re.search(r"default via (\S+) dev (\S+)", out)
        return (m.group(1), m.group(2)) if m else ("", "")
    if system == "Windows":
        out = _run(["route", "print", "-4", "0.0.0.0"])
        m = re.search(r"0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)", out)
        if m:
            gw, local_ip = m.group(1), m.group(2)
            for name, addrs in psutil.net_if_addrs().items():
                if any(a.family == socket.AF_INET and a.address == local_ip for a in addrs):
                    return gw, name
            return gw, ""
    return "", ""


def detect() -> NetworkInfo:
    gateway, iface = _default_route()
    addrs = psutil.net_if_addrs()
    candidates = [iface] if iface in addrs else []
    if not candidates:  # fall back: first up, non-loopback IPv4 interface
        stats = psutil.net_if_stats()
        candidates = [n for n in addrs if stats.get(n) and stats[n].isup and not n.startswith("lo")]
    for name in candidates:
        for a in addrs.get(name, []):
            if a.family == socket.AF_INET and a.netmask and not a.address.startswith("127."):
                net = ipaddress.ip_network(f"{a.address}/{a.netmask}", strict=False)
                return NetworkInfo(interface=name, ip=a.address, netmask=a.netmask,
                                   subnet=str(net), gateway=gateway)
    raise NetworkDetectError("no active IPv4 network found — connect to your hotspot first")
