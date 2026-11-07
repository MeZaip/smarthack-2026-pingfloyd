"""The local agent: everything the UI asks for that touches the network, the disk or the AI.

The UI (browser page) is a thin client: it calls /api/v1 (web/api_v1.py), which calls this module.
This module is the only place where the web app starts scans, re-checks a fix or asks the assistant.

* Live scans run in a background thread, one at a time, always on the network this computer is
  connected to (never a free-form target from the page), after explicit consent, through the same
  guardrail as the CLI. Only the nmap process is elevated (net/elevate.py, NFR-04).
* Results go into the local SQLite history (NFR-02: history stays on this computer).
"""
from __future__ import annotations

import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .. import history
from ..core.analysis import Analysis, analyze_file
from ..core.rules import evaluate, network_score
from ..net import elevate, guardrail, identify, netdetect, scanner

# ------------------------------------------------------------------ user-facing messages (RO / EN)
MESSAGES = {
    "no_network": ("Nu ești conectat la nicio rețea. Conectează-te la Wi-Fi și încearcă din nou.",
                   "You are not connected to a network. Connect to Wi-Fi and try again."),
    "refused": ("Această rețea nu poate fi verificată (nu pare o rețea de acasă).",
                "This network cannot be checked (it does not look like a home network)."),
    "need_consent": ("Trebuie să confirmi că rețeaua e a ta înainte să o verificăm.",
                     "Please confirm the network is yours before we check it."),
    "no_nmap": ("Lipsește o componentă necesară (Nmap). Instaleaz-o de pe nmap.org/download, apoi încearcă din nou.",
                "A required component (Nmap) is missing. Install it from nmap.org/download, then try again."),
    "denied": ("Ai apăsat „Nu” la cererea de permisiune. Fără permisiune nu putem verifica rețeaua. Încearcă din nou și apasă „Da”.",
               "You pressed \"No\" when asked for permission. Without it we cannot check the network. Try again and press \"Yes\"."),
    "unavailable": ("Calculatorul nu ne-a putut cere permisiunea de administrator. Pornește SafeHouse ca administrator.",
                    "The computer could not ask for administrator permission. Start SafeHouse as administrator."),
    "scan_failed": ("Verificarea nu s-a putut termina. Verifică dacă ești conectat la rețea și încearcă din nou.",
                    "The check could not finish. Make sure you are connected to the network and try again."),
    "busy": ("O verificare este deja în curs. Așteaptă să se termine.",
             "A check is already running. Please wait for it to finish."),
}


def message(code: str, lang: str) -> str:
    ro, en = MESSAGES.get(code, MESSAGES["scan_failed"])
    return ro if lang == "ro" else en


# ------------------------------------------------------------------ network facts for the consent screen
def _run(cmd: list[str]) -> str:
    kwargs = {"capture_output": True, "text": True, "timeout": 5}
    if os.name == "nt":
        kwargs["creationflags"] = elevate.NO_WINDOW
    try:
        return subprocess.run(cmd, **kwargs).stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def wifi_name() -> Optional[str]:
    """Name of the Wi-Fi network (SSID) we are on, for a friendly consent screen. None if unknown."""
    system = platform.system()
    if system == "Windows":
        m = re.search(r"^\s*SSID\s*:\s*(.+?)\s*$", _run(["netsh", "wlan", "show", "interfaces"]), re.M)
        return m.group(1) if m else None
    if system == "Linux":
        for line in _run(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"]).splitlines():
            if line.startswith("yes:"):
                return line[4:] or None
    return None


def network_info() -> dict:
    """{"ok": True, subnet, ip, gateway, wifi} or {"ok": False, "code": ...}. Never raises."""
    try:
        n = netdetect.detect()
    except netdetect.NetworkDetectError:
        return {"ok": False, "code": "no_network"}
    try:
        guardrail.check_target(n.subnet, guardrail.build_allowlist(n.subnet), confirmed=True)
    except guardrail.ScopeError:
        return {"ok": False, "code": "refused", "subnet": n.subnet}
    return {"ok": True, "subnet": n.subnet, "ip": n.ip, "gateway": n.gateway or None, "wifi": wifi_name()}


# ------------------------------------------------------------------ scan jobs
def scans_dir() -> Path:
    return Path(os.environ.get("NETCHECK_SCANS") or history.db_path().parent / "scans")


NmapRunner = Callable[[list[str]], subprocess.CompletedProcess]


@dataclass
class ScanJob:
    id: str
    subnet: str
    own_ip: Optional[str] = None     # this computer: scanned like every other device, but nmap cannot see
                                     # its own MAC, so we name it from the OS (see analyze_live)
    started: float = field(default_factory=time.time)
    finished: Optional[float] = None
    status: str = "running"          # running | done | error
    code: Optional[str] = None       # error code (see MESSAGES)
    scan_id: Optional[int] = None
    score: Optional[int] = None
    detail: Optional[str] = None     # technical reason (local only): shown under "Technical details" + logged

    def to_dict(self, lang: str) -> dict:
        return {
            "id": self.id, "status": self.status, "subnet": self.subnet,
            "elapsed": int((self.finished or time.time()) - self.started),
            "scan_id": self.scan_id, "score": self.score,
            "error": None if self.code is None else {"code": self.code, "message": message(self.code, lang),
                                                     "detail": self.detail},
        }


class ScanJobs:
    """At most one live scan at a time. `run_nmap` is injectable for tests."""

    def __init__(self, run_nmap: Optional[NmapRunner] = None,
                 on_saved: Optional[Callable[[int, Analysis], None]] = None):
        self._run_nmap = run_nmap
        self._on_saved = on_saved
        self._jobs: dict[str, ScanJob] = {}
        self._lock = threading.Lock()

    def current(self) -> Optional[ScanJob]:
        with self._lock:
            return next((j for j in self._jobs.values() if j.status == "running"), None)

    def get(self, job_id: str) -> Optional[ScanJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def start(self, confirmed: bool) -> ScanJob:
        """Validate, then start in the background. Raises ScanStartError(code) if it cannot start."""
        if not confirmed:
            raise ScanStartError("need_consent")
        try:
            net = netdetect.detect()
        except netdetect.NetworkDetectError:
            raise ScanStartError("no_network") from None
        try:   # the page can never choose the target: it is always the network we are on
            target = guardrail.check_target(net.subnet, guardrail.build_allowlist(net.subnet), confirmed=True)
        except guardrail.ScopeError:
            raise ScanStartError("refused") from None
        nmap = scanner.find_nmap()
        if self._run_nmap is None and not nmap:
            raise ScanStartError("no_nmap")
        with self._lock:
            if any(j.status == "running" for j in self._jobs.values()):
                raise ScanStartError("busy")
            job = ScanJob(id=uuid.uuid4().hex[:12], subnet=target, own_ip=net.ip or None)
            self._jobs[job.id] = job
        threading.Thread(target=self._work, args=(job, nmap or "nmap"), daemon=True).start()
        return job

    def _work(self, job: ScanJob, nmap: str) -> None:
        try:
            out = scans_dir()
            out.mkdir(parents=True, exist_ok=True)
            stamp = f"scan_{datetime.now():%Y%m%d_%H%M%S}"
            xml, errlog = out / f"{stamp}.xml", out / f"{stamp}.nmap.txt"
            cmd = identify.live_command(scanner.build_command(job.subnet, xml))   # + device-name discovery
            cmd[0] = nmap
            # the elevated nmap runs hidden (no stderr we can read on Windows): make it write its
            # errors/warnings to a text file next to the XML so a failure can be explained
            cmd[-1:-1] = ["-oN", str(errlog), "--log-errors"]
            run = self._run_nmap or (lambda c: elevate.run_elevated(c, timeout=900))
            try:
                proc = run(cmd)
            except elevate.ElevationDenied:
                return self._fail(job, "denied")
            except elevate.ElevationUnavailable as e:
                return self._fail(job, "unavailable", str(e))
            except subprocess.TimeoutExpired:
                return self._fail(job, "scan_failed", "nmap did not finish within 15 minutes")
            except OSError as e:
                return self._fail(job, "scan_failed", f"could not start nmap: {e}")
            # judge by the result file, not only the exit code (Windows/PowerShell can report odd codes)
            a = analyze_live(xml, job.own_ip) if xml.exists() else None
            if a is None or not a.ok:
                why = [f"nmap exit code {proc.returncode}"]
                why.append("no XML written" if a is None else f"XML unusable: {a.error}")
                why += [x for x in (_tail(errlog), (proc.stderr or "").strip()[-400:]) if x]
                return self._fail(job, "scan_failed", " | ".join(why))
            with history.open_history() as conn:
                scan_id, _ = history.save(conn, a)
            if self._on_saved:
                self._on_saved(scan_id, a)
            with self._lock:
                job.scan_id, job.score, job.status, job.finished = scan_id, a.score, "done", time.time()
        except Exception as e:  # noqa: BLE001 - a background job must never die silently
            self._fail(job, "scan_failed", f"{e.__class__.__name__}: {e}")

    def _fail(self, job: ScanJob, code: str, detail: Optional[str] = None) -> None:
        with self._lock:
            job.status, job.code, job.detail, job.finished = "error", code, detail, time.time()
        print(f"[netcheck] scan {job.id} on {job.subnet} failed: {code}" + (f" - {detail}" if detail else ""),
              file=sys.stderr, flush=True)


def _tail(path: Path, lines: int = 6) -> str:
    """Last lines of nmap's own log that look like errors/warnings."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    keep = [x for x in text if not x.startswith("#") and x.strip()]
    return " / ".join(keep[-lines:])[:600]


def this_computer_name() -> Optional[str]:
    name = socket.gethostname().split(".")[0]
    return name if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,62}", name or "") else None


def analyze_live(xml: Path, own_ip: Optional[str] = None) -> Analysis:
    """Like core.analysis.analyze_file, plus the device names we really know (net/identify.py):
    names devices announce themselves, and this computer's own name from the OS (nmap never
    reports the MAC of the computer it runs on). Rules and scoring are unchanged."""
    a = analyze_file(xml)
    if not a.ok:
        return a
    try:
        names = identify.discovered_names(xml.read_bytes())
    except OSError:
        names = {}
    if own_ip and own_ip not in names:
        me = this_computer_name()
        if me:
            names[own_ip] = me
    changed = False
    for h in a.scan.hosts:
        if not h.hostnames and h.ip in names:
            h.hostnames = [names[h.ip]]
            changed = True
    if changed:
        a.findings = evaluate(a.scan)
        a.score = network_score(a.findings)
    return a


class ScanStartError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ------------------------------------------------------------------ app mode (started with `netcheck app`)
class AppLife:
    """When started by the launcher: a heartbeat from the open page keeps the agent alive;
    the "Close" button or a closed window (no heartbeat) stops it."""

    IDLE_SECONDS = 90

    def __init__(self):
        self.app_mode = os.environ.get("NETCHECK_APP_MODE") == "1"
        self.last_seen: Optional[float] = None
        self._stop: Optional[Callable[[], None]] = None

    def on_stop(self, fn: Callable[[], None]) -> None:
        self._stop = fn

    def heartbeat(self) -> None:
        self.last_seen = time.time()

    def idle(self, now: Optional[float] = None) -> bool:
        return self.last_seen is not None and (now or time.time()) - self.last_seen > self.IDLE_SECONDS

    def stop(self) -> bool:
        if self._stop is None:
            return False
        threading.Timer(0.3, self._stop).start()   # let the HTTP response go out first
        return True
