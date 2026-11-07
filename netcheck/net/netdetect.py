"""FR-01: find the active interface, its subnet and gateway with no manual input.

Uses psutil when installed; otherwise parses `route`/`ifconfig` (macOS) or `ip` (Linux),
so the core stays standard-library only.
"""
from __future__ import annotations

import ipaddress
import platform
import re
import subprocess
from dataclasses import asdict, dataclass


@dataclass
class NetworkInfo:
    interface: str
    ip: str
    netmask: str
    subnet: str        # e.g. "172.20.10.0/28" (iPhone hotspot); Android varies
    gateway: str       # "" if unknown

    def to_dict(self) -> dict:
        return asdict(self)

    def contract_network(self) -> dict:
        """The 'network' object of service_data_contracts.md §1."""
        return {"subnet": self.subnet, "gateway": self.gateway or None}


class NetworkDetectError(Exception):
    pass


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


# ------------------------------------------------------------------ pure parsers (unit-tested)
def parse_macos_route(text: str) -> tuple[str, str]:
    gw = re.search(r"gateway:\s*(\S+)", text)
    iface = re.search(r"interface:\s*(\S+)", text)
    return (gw.group(1) if gw else "", iface.group(1) if iface else "")


def parse_linux_route(text: str) -> tuple[str, str]:
    m = re.search(r"default via (\S+) dev (\S+)", text)
    return (m.group(1), m.group(2)) if m else ("", "")


def parse_ifconfig(text: str) -> tuple[str, str] | None:
    """macOS `ifconfig en0` -> (ip, dotted netmask). Netmask is printed in hex (0xfffffff0)."""
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+) netmask (0x[0-9a-fA-F]{8}|\d+\.\d+\.\d+\.\d+)", text)
    if not m:
        return None
    mask = m.group(2)
    if mask.startswith("0x"):
        mask = str(ipaddress.IPv4Address(int(mask, 16)))
    return m.group(1), mask


def parse_ip_addr(text: str) -> tuple[str, str] | None:
    """Linux `ip -o -4 addr show dev wlan0` -> (ip, dotted netmask)."""
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", text)
    if not m:
        return None
    return m.group(1), str(ipaddress.IPv4Network(f"0.0.0.0/{m.group(2)}").netmask)


# ------------------------------------------------------------------ detection
def _default_route() -> tuple[str, str]:
    system = platform.system()
    if system == "Darwin":
        return parse_macos_route(_run(["route", "-n", "get", "default"]))
    if system == "Linux":
        return parse_linux_route(_run(["ip", "-4", "route", "show", "default"]))
    if system == "Windows":
        out = _run(["route", "print", "-4", "0.0.0.0"])
        m = re.search(r"0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)", out)
        return (m.group(1), "ip:" + m.group(2)) if m else ("", "")
    return "", ""


def _addr_psutil(iface: str):
    try:
        import psutil
        import socket
    except ImportError:
        return None
    addrs = psutil.net_if_addrs()
    for name, entries in addrs.items():
        for a in entries:
            if a.family != socket.AF_INET or not a.netmask or a.address.startswith("127."):
                continue
            if name == iface or iface == f"ip:{a.address}":
                return name, a.address, a.netmask
    return None


def _addr_shell(iface: str):
    if not iface or iface.startswith("ip:"):
        return None
    system = platform.system()
    if system == "Darwin":
        got = parse_ifconfig(_run(["ifconfig", iface]))
    elif system == "Linux":
        got = parse_ip_addr(_run(["ip", "-o", "-4", "addr", "show", "dev", iface]))
    else:
        got = None
    return (iface, *got) if got else None


def detect() -> NetworkInfo:
    gateway, iface = _default_route()
    found = _addr_psutil(iface) or _addr_shell(iface)
    if not found:
        hint = " (on Windows: pip install psutil)" if platform.system() == "Windows" else ""
        raise NetworkDetectError("no active IPv4 network found — connect to your hotspot first" + hint)
    name, ip, mask = found
    net = ipaddress.ip_network(f"{ip}/{mask}", strict=False)
    return NetworkInfo(interface=name, ip=ip, netmask=mask, subnet=str(net), gateway=gateway)
