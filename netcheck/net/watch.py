"""„Paznic" — quiet background guard. Runs WITHOUT root.

Each cycle:
  1. guardrail: still on the same (allowed) network? otherwise pause
  2. light discovery: unprivileged `nmap -sn` (or a ping sweep) fills the OS ARP table, then we read it
  3. unprivileged top-100 TCP connect scan of the devices we see
  4. compare with what we knew -> events new_device / new_port (+ desktop notification)

Privacy (NFR-02): devices are remembered by HMAC(local secret, MAC); the raw MAC is never stored.
State lives in $NETCHECK_HOME (default ~/.netcheck) with owner-only permissions.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..core.device import mask_mac
from ..core.models import Host, Port
from ..core.parser import ScanFileError, parse_bytes
from ..core.rules import evaluate_host
from . import guardrail, netdetect

_ARP_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})\b.*?(?<![0-9a-fA-F:-])"
                     r"((?:[0-9a-fA-F]{1,2}[:-]){5}[0-9a-fA-F]{1,2})(?![0-9a-fA-F:-])")


# ------------------------------------------------------------------ local private storage
def home() -> Path:
    p = Path(os.environ.get("NETCHECK_HOME") or (Path.home() / ".netcheck"))
    p.mkdir(mode=0o700, parents=True, exist_ok=True)
    return p


def _secret() -> bytes:
    path = home() / "watch_secret"
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(secrets.token_bytes(32))
    return path.read_bytes()


def device_id(mac: str, ip: str) -> str:
    basis = f"mac:{mac.upper()}" if mac else f"ip:{ip}"
    return hmac.new(_secret(), basis.encode(), hashlib.sha256).hexdigest()[:12]


def _state_path(subnet: str) -> Path:
    return home() / f"watch_{subnet.replace('/', '_')}.json"


def load_state(subnet: str) -> dict:
    try:
        return json.loads(_state_path(subnet).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(subnet: str, state: dict) -> None:
    path = _state_path(subnet)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(state, fh)


def log_event(line: str) -> None:
    with open(home() / "watch_events.log", "a", encoding="utf-8") as fh:
        fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")


# ------------------------------------------------------------------ discovery
def parse_arp(text: str, subnet: str) -> dict[str, str]:
    """ARP/neighbour table (macOS `arp -an`, Linux `ip neigh`, Windows `arp -a`) -> {ip: mac} in subnet."""
    net = ipaddress.ip_network(subnet, strict=False)
    out = {}
    for line in text.splitlines():
        if "incomplete" in line.lower():
            continue
        m = _ARP_RE.search(line)
        if not m:
            continue
        ip = m.group(1)
        mac = ":".join(p.zfill(2) for p in m.group(2).replace("-", ":").lower().split(":"))
        if mac in ("ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00") or mac.startswith("01:00:5e"):
            continue
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if a in net and a not in (net.network_address, net.broadcast_address):
            out[ip] = mac
    return out


def read_arp_table() -> str:
    for cmd in (["arp", "-an"], ["ip", "neigh"], ["arp", "-a"]):
        if shutil.which(cmd[0]):
            try:
                return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
            except (OSError, subprocess.TimeoutExpired):
                continue
    return ""


def discover(subnet: str) -> None:
    """Make every live host answer once so it lands in the ARP table (rate-limited, unprivileged)."""
    if shutil.which("nmap"):
        subprocess.run(["nmap", "-sn", "-n", "--max-rate", "100", subnet], capture_output=True, timeout=120)
        return
    hosts = [str(h) for h in ipaddress.ip_network(subnet, strict=False).hosts()]
    system = platform.system()
    count = ["-n", "1"] if system == "Windows" else ["-c", "1"]
    wait = ["-W", "1000"] if system == "Darwin" else (["-w", "1000"] if system == "Windows" else ["-W", "1"])
    with ThreadPoolExecutor(max_workers=20) as pool:  # ~20 in flight -> well under 100 pkt/s
        list(pool.map(lambda h: subprocess.run(["ping", *count, *wait, h], capture_output=True), hosts))


def quick_ports(ips: list[str]) -> dict[str, list[Port]]:
    """Unprivileged top-100 TCP connect scan -> {ip: [open Port]}."""
    if not ips or not shutil.which("nmap"):
        return {}
    proc = subprocess.run(["nmap", "-sT", "-Pn", "-n", "--top-ports", "100", "-sV", "--version-light",
                           "--max-rate", "100", "-oX", "-", *ips], capture_output=True, timeout=600)
    try:
        scan = parse_bytes(proc.stdout, source="watch")
    except ScanFileError:
        return {}
    return {h.ip: h.open_ports for h in scan.hosts}


# ------------------------------------------------------------------ comparison (unit-tested)
@dataclass
class Event:
    kind: str          # new_device | new_port
    device_id: str
    ip: str
    detail: str
    risks: list[str] = field(default_factory=list)


def compare(known: dict, observed: dict[str, str], ports: dict[str, list[Port]]) -> tuple[list[Event], dict]:
    """known: {device_id: {"ip", "mac_masked", "ports": [[port, proto], ...]}} -> (events, new_known)."""
    events, new_known = [], {k: dict(v) for k, v in known.items()}
    for ip, mac in sorted(observed.items()):
        did = device_id(mac, ip)
        plist = ports.get(ip, [])
        probe = Host(ip=ip, status="up", mac=mac, vendor="?", hostnames=["?"], ports=plist)
        risky = [f"{f.code}:{f.port}" for f in evaluate_host(probe) if f.points > 0]
        if did not in known:
            events.append(Event("new_device", did, ip, f"MAC {mask_mac(mac)}, {len(plist)} open port(s)", risky))
        else:
            old = {tuple(x) for x in known[did].get("ports", [])}
            for p in plist:
                if (p.portid, p.protocol) not in old:
                    events.append(Event("new_port", did, ip, f"{p.portid}/{p.protocol} {p.service}",
                                        [r for r in risky if r.endswith(f":{p.portid}")]))
        new_known[did] = {"ip": ip, "mac_masked": mask_mac(mac),
                          "ports": sorted([p.portid, p.protocol] for p in plist)}
    return events, new_known


def describe(e: Event, lang: str) -> tuple[str, str]:
    risk = (" ⚠ " + ("risc: " if lang == "ro" else "risk: ") + ", ".join(e.risks)) if e.risks else ""
    if e.kind == "new_device":
        return ("🛡️ Dispozitiv nou în Wi-Fi" if lang == "ro" else "🛡️ New device on your Wi-Fi",
                f"{e.ip} — {e.detail}{risk}")
    return ("🛡️ Ușă nouă deschisă" if lang == "ro" else "🛡️ New door opened", f"{e.ip} — {e.detail}{risk}")


def notify(title: str, text: str) -> None:
    """Desktop notification. Text goes in argv, never into a script string (no injection)."""
    try:
        if platform.system() == "Darwin" and shutil.which("osascript"):
            subprocess.run(["osascript", "-e", "on run argv", "-e",
                            "display notification (item 2 of argv) with title (item 1 of argv)",
                            "-e", "end run", title, text], capture_output=True, timeout=5)
            return
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", title, text], capture_output=True, timeout=5)
            return
    except (OSError, subprocess.TimeoutExpired):
        pass
    print("\a", end="")


def run(interval: int = 60, lang: str = "ro", extra_allow: list[str] | None = None,
        cycles: int | None = None) -> int:
    start = netdetect.detect()
    subnet = guardrail.check_target(start.subnet, guardrail.build_allowlist(start.subnet, extra_allow),
                                    confirmed=True)
    known = load_state(subnet)
    first = not known
    print(("Paznicul păzește " if lang == "ro" else "Guarding ") + f"{subnet} (Ctrl+C = stop)")
    n = 0
    try:
        while cycles is None or n < cycles:
            n += 1
            try:
                now = netdetect.detect()
            except netdetect.NetworkDetectError:
                now = None
            if now is None or now.subnet != start.subnet:
                msg = "Rețea nouă, nu scanez (pauză)." if lang == "ro" else "Different network, not scanning (paused)."
                print("⏸ " + msg)
                log_event("paused " + msg)
            else:
                discover(subnet)
                observed = parse_arp(read_arp_table(), subnet)
                observed.pop(now.ip, None)
                events, known = compare(known, observed, quick_ports(sorted(observed)))
                save_state(subnet, known)
                if first:
                    msg = (f"Am memorat {len(known)} dispozitive. De acum te anunț dacă apare ceva nou."
                           if lang == "ro" else f"Remembered {len(known)} devices. I'll tell you if anything new appears.")
                    print("✔ " + msg)
                    log_event("baseline " + msg)
                    first = False
                else:  # after the baseline, everything new is an alert
                    for e in events:
                        title, text = describe(e, lang)
                        print(f"{title}: {text}")
                        log_event(f"{e.kind} {text}")
                        notify(title, text)
            if cycles is None or n < cycles:
                time.sleep(interval)
    except KeyboardInterrupt:
        print()
    return 0
