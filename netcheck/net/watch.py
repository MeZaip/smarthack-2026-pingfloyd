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
from .scanner import find_nmap

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
    cmds = ([["arp", "-a"]] if platform.system() == "Windows"          # Windows arp has no -n
            else [["arp", "-an"], ["ip", "neigh"], ["arp", "-a"]])
    for cmd in cmds:
        if shutil.which(cmd[0]):
            try:
                return subprocess.run(cmd, capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL,
                                      creationflags=_NO_WINDOW).stdout
            except (OSError, subprocess.TimeoutExpired):
                continue
    return ""


def macs_from_xml(data: bytes, subnet: str) -> dict[str, str]:
    """{ip: mac} of the hosts nmap saw up in `subnet` (nmap -sn -oX -)."""
    try:
        scan = parse_bytes(data, source="discover")
    except ScanFileError:
        return {}
    net = ipaddress.ip_network(subnet, strict=False)
    out = {}
    for h in scan.hosts:
        if h.status != "up" or not h.mac:
            continue
        try:
            if ipaddress.ip_address(h.ip) not in net:
                continue
        except ValueError:
            continue
        out[h.ip] = ":".join(p.zfill(2) for p in h.mac.replace("-", ":").lower().split(":"))
    return out


# what the last look did, shown under "Advanced details" of the guard card (helps when it sees too few devices)
last_look: dict = {}
_running: set = set()
_running_lock = __import__("threading").Lock()
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0      # no console window flashing on Windows


def _run(cmd: list[str], timeout: float) -> subprocess.CompletedProcess:
    """subprocess.run that `kill_running()` can stop at once (guard turned off / network changed)."""
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=_NO_WINDOW)
    with _running_lock:
        _running.add(proc)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise
    finally:
        with _running_lock:
            _running.discard(proc)
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def kill_running() -> None:
    with _running_lock:
        procs = list(_running)
    for p in procs:
        try:
            p.kill()
        except OSError:
            pass


def discover(subnet: str) -> dict[str, str]:
    """Make every live host answer once (rate-limited, no admin rights) and return {ip: mac} of the ones nmap saw.
    On Windows (Npcap) nmap does its own ARP, so the answers are NOT in the system ARP table: its list is needed;
    without admin rights on Linux/macOS it uses normal connections and the ARP table fills itself."""
    nmap = find_nmap()
    last_look.clear()
    last_look.update(subnet=subnet, nmap=nmap or None)
    if nmap:
        try:
            done = _run([nmap, "-sn", "-n", "--max-rate", "100", "-oX", "-", subnet], timeout=120)
            last_look.update(how="nmap", nmap_rc=done.returncode,
                             nmap_err=done.stderr.decode("utf-8", "replace").strip()[:200])
            if done.returncode == 0:
                found = macs_from_xml(done.stdout, subnet)
                up = done.stdout.count(b'state="up"')
                last_look.update(from_nmap=len(found), nmap_up=up)
                return found
        except (OSError, subprocess.TimeoutExpired) as e:
            last_look.update(how="nmap", nmap_err=f"{e.__class__.__name__}: {str(e)[:160]}")
    last_look["how"] = "ping"
    hosts = [str(h) for h in ipaddress.ip_network(subnet, strict=False).hosts()]
    system = platform.system()
    count = ["-n", "1"] if system == "Windows" else ["-c", "1"]
    wait = ["-W", "1000"] if system == "Darwin" else (["-w", "1000"] if system == "Windows" else ["-W", "1"])
    with ThreadPoolExecutor(max_workers=20) as pool:  # ~20 in flight -> well under 100 pkt/s
        list(pool.map(lambda h: subprocess.run(["ping", *count, *wait, h], capture_output=True, stdin=subprocess.DEVNULL,
                                               creationflags=_NO_WINDOW), hosts))
    return {}


def quick_ports(ips: list[str]) -> dict[str, list[Port]]:
    """Unprivileged top-100 TCP connect scan -> {ip: [open Port]}. Fast on purpose (an alert, not the graded
    analysis): no version probes, service names from nmap's port table, one retry, at most 45 s per device."""
    nmap = find_nmap()
    if not ips or not nmap:
        return {}
    try:
        proc = _run([nmap, "-sT", "-Pn", "-n", "--top-ports", "100", "-T4", "--max-retries", "1",
                     "--host-timeout", "45s", "--max-rate", "100", "-oX", "-", *ips], timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return {}
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
        if ip not in ports and did in known:        # its doors could not be checked this time: keep what we knew
            new_known[did] = {**known[did], "ip": ip}
            continue
        plist = ports.get(ip, [])
        probe = Host(ip=ip, status="up", mac=mac, vendor="?", hostnames=["?"], ports=plist)
        risky = [f"{f.code}:{f.port}" for f in evaluate_host(probe) if f.points > 0]
        if did not in known:
            events.append(Event("new_device", did, ip, f"MAC {mask_mac(mac)}, {len(plist)} open port(s)", risky))
        elif known[did].get("ports") is None:
            pass                              # its doors were never checked before: this is the first look
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
                found = discover(subnet)
                observed = {**found, **parse_arp(read_arp_table(), subnet)}
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


# ------------------------------------------------------------------ maker from the MAC (nmap's own list, offline)
_OUI: dict[str, str] | None = None


def _oui_table() -> dict[str, str]:
    global _OUI
    if _OUI is None:
        _OUI = {}
        nmap = find_nmap()
        here = [Path(os.path.realpath(nmap)).parent] if nmap else []
        places = [p / "nmap-mac-prefixes" for p in here] + [p.parent / "share" / "nmap" / "nmap-mac-prefixes" for p in here] + [
            Path(p) for p in ("/opt/homebrew/share/nmap/nmap-mac-prefixes", "/usr/local/share/nmap/nmap-mac-prefixes",
                              "/usr/share/nmap/nmap-mac-prefixes", r"C:\Program Files (x86)\Nmap\nmap-mac-prefixes",
                              r"C:\Program Files\Nmap\nmap-mac-prefixes")]
        for path in places:
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if len(line) > 7 and line[6] == " " and not line.startswith("#"):
                            _OUI[line[:6].upper()] = line[7:].strip()[:60]
                break
            except OSError:
                continue
    return _OUI


def mac_vendor(mac: str) -> str | None:
    """Maker of a device from the first half of its MAC (None for private / random MACs)."""
    clean = (mac or "").replace(":", "").replace("-", "").upper()
    if len(clean) < 6:
        return None
    try:
        if int(clean[:2], 16) & 0x02:
            return None
    except ValueError:
        return None
    return _oui_table().get(clean[:6])


def is_private(mac: str) -> bool:
    try:
        return bool(int((mac or "").replace("-", ":").split(":")[0], 16) & 0x02)
    except ValueError:
        return False


def forget_all() -> None:
    """„Delete my history" also forgets what the guard remembered (NFR-02)."""
    for f in home().glob("watch_*"):
        try:
            f.unlink()
        except OSError:
            pass


# ------------------------------------------------------------------ the guard inside the app (one thread, no root)
class Guard:
    """„Păzește casa": every `interval` seconds looks at who is on the network (unprivileged), tells about a new
    device as soon as it is seen and, after a quick TCP check of its doors, about risky open doors. Only the
    network this computer is connected to, only after the user's confirmation, paused on any other network."""

    MAX_EVENTS = 30

    def __init__(self, interval: int = 20, detect=None, discover_fn=None, arp_fn=None, ports_fn=None, busy=None):
        import threading
        self.interval = interval
        self._detect = detect or netdetect.detect
        self._discover = discover_fn or discover
        self._arp = arp_fn or read_arp_table
        self._ports = ports_fn or quick_ports
        self._busy = busy or (lambda: False)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self.on = False
        self.subnet = self.my_ip = None
        self.state = "off"           # off | learning | watching | paused | error
        self.last_check = None
        self.known: dict = {}
        self.events: list[dict] = []
        self.phase = None            # looking | doors (what the current look is doing)
        self.seen = 0                # devices seen at the last look
        self.error = None            # short reason when state == "error"
        self.net_now = None          # the network seen by the last network check
        self.arp_count = None        # devices in the system ARP table at the last look

    # ---------------------------------------------------------- control
    def start(self, subnet: str, my_ip: str | None) -> None:
        import threading
        guardrail.check_target(subnet, guardrail.build_allowlist(subnet), confirmed=True)
        with self._lock:
            if self.on and self.subnet == subnet:
                return
            self.stop_locked()
            self.on, self.subnet, self.my_ip = True, subnet, my_ip
            self.known = load_state(subnet)
            self.state = "watching" if self.known else "learning"
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._loop, name="safehouse-guard", daemon=True)
            self._thread.start()
            threading.Thread(target=self._net_loop, args=(self._stop,), name="safehouse-guard-net", daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            self.stop_locked()

    def stop_locked(self) -> None:
        self._stop.set()
        self.on = False
        self.state, self.phase = "off", None
        if self._discover is discover or self._ports is quick_ports:
            kill_running()                    # stop a running nmap right away

    def forget(self) -> None:
        with self._lock:
            self.stop_locked()
            self.known, self.events = {}, []
        forget_all()

    def ack(self, event_id: str, mine: bool) -> bool:
        with self._lock:
            ev = next((e for e in self.events if e["id"] == event_id), None)
            if ev is None:
                return False
            ev["status"] = "mine" if mine else "stranger"
            if ev["device"] in self.known:
                self.known[ev["device"]]["mine"] = mine
                if self.subnet:
                    save_state(self.subnet, self.known)
            return True

    def status(self) -> dict:
        with self._lock:
            diag = {**last_look, "net_now": self.net_now, "arp": self.arp_count} if self._discover is discover else {}
            return {"on": self.on, "state": self.state, "phase": self.phase, "seen": self.seen, "error": self.error, "diag": diag,
                    "subnet": self.subnet, "interval": self.interval, "last_check": self.last_check,
                    "known": len(self.known), "events": [dict(e) for e in reversed(self.events)]}

    # ---------------------------------------------------------- work
    NET_EVERY = 5

    def _net_loop(self, stop) -> None:
        """Every few seconds, even while a look is running: still on the network the user confirmed?"""
        while not stop.wait(self.NET_EVERY):
            try:
                now = self._detect()
            except netdetect.NetworkDetectError:
                now = None
            except Exception:  # noqa: BLE001
                continue
            with self._lock:
                if stop.is_set():
                    return
                self.net_now = now.subnet if now else None
                if now is not None and now.subnet != self.subnet:
                    self.stop_locked()
                    self.state = "moved"
                    return

    def _loop(self) -> None:
        stop = self._stop
        while not stop.is_set():
            try:
                self.check_once(stop)
            except Exception as e:  # noqa: BLE001 - the guard must never take the app down
                import sys
                import traceback
                traceback.print_exc(file=sys.stderr)          # app.log, for us
                with self._lock:
                    self.phase = None
                    if not stop.is_set():
                        self.state, self.error = "error", f"{e.__class__.__name__}: {str(e)[:160]}"
            stop.wait(self.interval)

    def _event(self, kind: str, did: str, ip: str, mac: str, ports: list | None = None, risks: list | None = None) -> dict:
        import uuid
        ev = {"id": uuid.uuid4().hex[:10], "kind": kind, "when": int(time.time()), "device": did, "ip": ip,
              "mac": mask_mac(mac), "vendor": mac_vendor(mac), "private_mac": is_private(mac),
              "ports": ports or [], "risks": risks or [], "status": "new", "checking": kind == "new_device"}
        self.events.append(ev)
        del self.events[:-self.MAX_EVENTS]
        return ev

    def check_once(self, stop=None) -> None:
        stop = stop or self._stop
        if self._busy():                      # a full check is running: do not scan at the same time
            with self._lock:
                self.phase = "waiting"
            return
        try:
            now = self._detect()
        except netdetect.NetworkDetectError:
            now = None
        with self._lock:
            subnet, my_ip, learning = self.subnet, self.my_ip, not self.known
            if now is None:
                self.state, self.phase = "paused", None       # no network for a moment (Wi-Fi reconnecting)
                return
            if now.subnet != subnet:                          # another network: the consent was for the old one
                self.stop_locked()
                self.state = "moved"
                return
            self.state = "learning" if learning else "watching"
            self.phase, self.error = "looking", None
        found = self._discover(subnet) or {}
        table = parse_arp(self._arp(), subnet)
        self.arp_count = len(table)
        observed = {**found, **table}
        observed.pop(my_ip, None)
        if now.ip:
            observed.pop(now.ip, None)
        if stop.is_set():
            return
        with self._lock:
            if stop.is_set():
                return
            self.seen = len(observed)
            if learning:              # remember who is here right away; their doors are checked next
                for ip, mac in observed.items():
                    self.known.setdefault(device_id(mac, ip), {"ip": ip, "mac_masked": mask_mac(mac), "ports": None})
                save_state(subnet, self.known)
                self.state = "watching"
            self.phase = "doors"
        # 1. a new device is told right away; its doors are checked next
        fresh = {}
        with self._lock:
            for ip, mac in sorted(observed.items()):
                did = device_id(mac, ip)
                if did not in self.known and not learning:
                    fresh[did] = self._event("new_device", did, ip, mac)
        ports = self._ports(sorted(observed))
        if stop.is_set():
            return
        events, known = compare(self.known, observed, ports)
        with self._lock:
            if stop.is_set():                 # turned off (or another network) meanwhile: keep nothing
                return
            for did, data in known.items():          # keep what the user said about a device
                if "mine" in self.known.get(did, {}):
                    data["mine"] = self.known[did]["mine"]
            for e in events:
                plist = [f"{p.portid}/{p.protocol} {p.service}".strip() for p in ports.get(e.ip, [])]
                if e.kind == "new_device" and e.device_id in fresh:
                    fresh[e.device_id].update(ports=plist, risks=[r.split(":")[0] for r in e.risks], checking=False)
                elif e.kind == "new_port" and not learning:
                    self._event("new_port", e.device_id, e.ip, observed.get(e.ip, ""), ports=[e.detail],
                                risks=[r.split(":")[0] for r in e.risks])["checking"] = False
            for ev in fresh.values():
                ev["checking"] = False
            self.known = known
            save_state(subnet, known)
            self.last_check = int(time.time())
            self.state, self.phase = "watching", None
