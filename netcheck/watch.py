"""„Paznic" — quiet background guard. Runs WITHOUT root.

Each cycle:
  1. guardrail: still on the same (allowed) network? otherwise pause
  2. light discovery: unprivileged `nmap -sn` (or a ping sweep) fills the OS ARP table, then we read it
  3. unprivileged top-100 TCP connect scan of the devices we see
  4. compare with what we knew -> events: new_device, new_port (+ notification)
"""
from __future__ import annotations

import ipaddress
import platform
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import guardrail, history, netdetect
from .identity import device_id
from .models import mask_mac
from .parser import ScanFileError, parse_bytes
from .rules import classify_host

_ARP_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})\b.*?(?<![0-9a-fA-F:-])((?:[0-9a-fA-F]{1,2}[:-]){5}[0-9a-fA-F]{1,2})(?![0-9a-fA-F:-])")


def parse_arp(text: str, subnet: str) -> dict[str, str]:
    """ARP/neighbour table text (macOS, Linux `ip neigh`, Windows) -> {ip: mac} inside subnet."""
    net = ipaddress.ip_network(subnet, strict=False)
    out = {}
    for line in text.splitlines():
        if "incomplete" in line.lower():
            continue
        m = _ARP_RE.search(line)
        if not m:
            continue
        ip, mac = m.group(1), m.group(2).replace("-", ":").lower()
        mac = ":".join(p.zfill(2) for p in mac.split(":"))
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
    flag = ["-W", "1000"] if platform.system() == "Darwin" else (["-w", "1000"] if platform.system() == "Windows"
                                                                  else ["-W", "1"])
    count = ["-n", "1"] if platform.system() == "Windows" else ["-c", "1"]
    with ThreadPoolExecutor(max_workers=20) as pool:  # ~20 pings in flight -> well under 100 pkt/s
        list(pool.map(lambda h: subprocess.run(["ping", *count, *flag, h], capture_output=True), hosts))


def quick_ports(ips: list[str]) -> dict[str, list[dict]]:
    """Unprivileged top-100 TCP connect scan -> {ip: [port dicts]}."""
    if not ips or not shutil.which("nmap"):
        return {}
    proc = subprocess.run(["nmap", "-sT", "-Pn", "-n", "--top-ports", "100", "-sV", "--version-light",
                           "--max-rate", "100", "-oX", "-", *ips], capture_output=True, timeout=600)
    try:
        hosts = parse_bytes(proc.stdout)
    except ScanFileError:
        return {}
    return {h.ip: [{"port": p.portid, "protocol": p.protocol, "service": p.service, "product": p.product,
                    "version": p.version, "title": p.title} for p in h.open_ports] for h in hosts}


@dataclass
class Event:
    kind: str          # new_device | new_port | paused
    device_id: str
    ip: str
    detail: str
    findings: list[str] = field(default_factory=list)


def compare(known: dict, observed: dict[str, str], ports: dict[str, list[dict]]) -> tuple[list[Event], dict]:
    """known: {device_id: {"ip", "mac_masked", "ports": [[port, proto], ...]}} -> (events, new_known)."""
    from .models import Host, Port
    events, new_known = [], {k: dict(v) for k, v in known.items()}
    for ip, mac in sorted(observed.items()):
        did = device_id(mac, ip)
        plist = ports.get(ip, [])
        pset = sorted([p["port"], p["protocol"]] for p in plist)
        host = Host(ip=ip, mac=mac, vendor="?", hostname="?", ports=[
            Port(protocol=p["protocol"], portid=p["port"], state="open", service=p["service"],
                 product=p["product"], version=p["version"], title=p.get("title", "")) for p in plist])
        risky = [f"{f.code}:{f.port}" for f in classify_host("watch", host) if f.points > 0]
        if did not in known:
            events.append(Event("new_device", did, ip, f"MAC {mask_mac(mac)}, {len(plist)} open port(s)", risky))
        else:
            old = {tuple(x) for x in known[did].get("ports", [])}
            for p in plist:
                if (p["port"], p["protocol"]) not in old:
                    f = [r for r in risky if r.endswith(f":{p['port']}")]
                    events.append(Event("new_port", did, ip, f"{p['port']}/{p['protocol']} {p['service']}", f))
        new_known[did] = {"ip": ip, "mac_masked": mask_mac(mac), "ports": pset}
    return events, new_known


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


def describe(e: Event, lang: str) -> tuple[str, str]:
    nick = history.nicknames().get(e.device_id)
    who = f"„{nick}” ({e.ip})" if nick else e.ip
    risk = (" ⚠ " + ("risc: " if lang == "ro" else "risk: ") + ", ".join(e.findings)) if e.findings else ""
    if e.kind == "new_device":
        return (("🛡️ Dispozitiv nou în Wi-Fi" if lang == "ro" else "🛡️ New device on your Wi-Fi"),
                f"{who} — {e.detail}{risk}")
    if e.kind == "new_port":
        return (("🛡️ Ușă nouă deschisă" if lang == "ro" else "🛡️ New door opened"), f"{who} — {e.detail}{risk}")
    return ("🛡️ Paznic", e.detail)


def run(interval: int = 60, lang: str = "ro", extra_allow: list[str] | None = None, cycles: int | None = None) -> int:
    start = netdetect.detect()
    allow = guardrail.build_allowlist(start.subnet, extra_allow)
    subnet = guardrail.check_target(start.subnet, allow, confirmed=True)
    key = f"watch:{subnet}"
    known = history.kv_get(key, {})
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
                msg = ("Rețea nouă, nu scanez (pauză)." if lang == "ro" else "Different network, not scanning (paused).")
                print("⏸ " + msg)
                history.add_watch_event("paused", "", "", msg)
            else:
                discover(subnet)
                observed = parse_arp(read_arp_table(), subnet)
                observed.pop(now.ip, None)
                events, known = compare(known, observed, quick_ports(sorted(observed)))
                history.kv_set(key, known)
                history.kv_set("watch:last_check", {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "subnet": subnet,
                                                    "devices": len(known)})
                if first:
                    msg = (f"Am memorat {len(known)} dispozitive. De acum te anunț dacă apare ceva nou."
                           if lang == "ro" else f"Remembered {len(known)} devices. I'll tell you if anything new appears.")
                    print("✔ " + msg)
                    history.add_watch_event("baseline", "", "", msg)
                    first = False
                else:
                    for e in events:
                        title, text = describe(e, lang)
                        print(f"{title}: {text}")
                        history.add_watch_event(e.kind, e.device_id, e.ip, text)
                        notify(title, text)
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
    return 0
