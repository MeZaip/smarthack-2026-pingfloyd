"""„Paznic" (FR-13) started from the web UI: periodic, unprivileged rescans + compare with what we knew.

Same building blocks and the same on-disk memory as `netcheck watch` (net/watch.py), so the CLI and the
UI share one baseline. No root (NFR-04), nothing is sniffed: each cycle actively asks the devices
(ping/ARP discovery + top-100 TCP connect scan), as allowed by the rules of engagement.
The catalogue rules (core.rules.evaluate_host) flag which new ports are risky.

Rules: the target is always the connected subnet, checked by the guardrail every cycle; if the laptop
changes network the guard pauses. While a full live scan runs the guard skips its cycle, so the two
never add up to more than ~100 packets/s.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..net import guardrail, netdetect, watch

MIN_INTERVAL, MAX_INTERVAL = 30, 3600
MAX_EVENTS = 50


@dataclass
class GuardEvent:
    at: float
    event: watch.Event

    def text(self, lang: str) -> tuple[str, str]:
        return watch.describe(self.event, lang)

    @property
    def risky(self) -> bool:
        return bool(self.event.risks)


@dataclass
class GuardState:
    running: bool = False
    stopping: bool = False
    subnet: str = ""
    interval: int = 300
    started: Optional[float] = None
    last_check: Optional[float] = None
    cycles: int = 0
    known: int = 0
    baseline: bool = False          # True once the first cycle remembered the devices
    status: str = "idle"            # idle | checking | waiting | paused | skipped | error
    message: str = ""
    events: deque = field(default_factory=lambda: deque(maxlen=MAX_EVENTS))


_lock = threading.Lock()
_state = GuardState()
_stop = threading.Event()
_thread: Optional[threading.Thread] = None
_busy: Callable[[], bool] = lambda: False     # set by the app: "is a full live scan running?"


class AlreadyRunning(Exception):
    pass


def state() -> GuardState:
    return _state


def set_busy_check(fn: Callable[[], bool]) -> None:
    global _busy
    _busy = fn


def check(confirmed: bool) -> netdetect.NetworkInfo:
    """Guardrail for the guard: connected subnet only, consent required. Raises ScopeError/NetworkDetectError."""
    net = netdetect.detect()
    guardrail.check_target(net.subnet, guardrail.build_allowlist(net.subnet), confirmed=confirmed)
    return net


def start(net: netdetect.NetworkInfo, interval: int) -> GuardState:
    global _thread, _state
    with _lock:
        if _state.running:
            raise AlreadyRunning(_state.subnet)
        known = watch.load_state(net.subnet)
        _state = GuardState(running=True, subnet=net.subnet, started=time.time(),
                            interval=max(MIN_INTERVAL, min(MAX_INTERVAL, int(interval))),
                            known=len(known), baseline=bool(known), status="checking",
                            events=_state.events)          # keep earlier alerts visible
        _stop.clear()
        _thread = threading.Thread(target=_loop, args=(net, _state), daemon=True, name="netcheck-guard")
        _thread.start()
        return _state


def stop() -> None:
    with _lock:
        if _state.running:
            _state.stopping = True
            _stop.set()


def forget() -> None:
    """NFR-02 'delete my history' also wipes the guard's memory (known devices + event log)."""
    stop()
    for p in watch.home().glob("watch_*.json"):
        p.unlink(missing_ok=True)
    (watch.home() / "watch_events.log").unlink(missing_ok=True)
    _state.events.clear()
    _state.known, _state.baseline = 0, False


def reset() -> None:  # tests
    global _state
    stop()
    if _thread:
        _thread.join(timeout=5)
    _state = GuardState()
    _stop.clear()


def run_cycle(net: netdetect.NetworkInfo, st: GuardState) -> None:
    """One check. Public so tests can drive it without threads or sleeping."""
    try:
        now = netdetect.detect()
    except netdetect.NetworkDetectError:
        now = None
    if now is None or now.subnet != net.subnet:
        st.status = "paused"
        watch.log_event("paused different network")
        return
    if _busy():
        st.status = "skipped"
        return
    st.status = "checking"
    watch.discover(st.subnet)
    observed = watch.parse_arp(watch.read_arp_table(), st.subnet)
    observed.pop(now.ip, None)
    events, known = watch.compare(watch.load_state(st.subnet), observed, watch.quick_ports(sorted(observed)))
    if _stop.is_set():                       # stopped (or history deleted) while we were scanning
        return
    watch.save_state(st.subnet, known)
    st.known, st.last_check, st.cycles = len(known), time.time(), st.cycles + 1
    if not st.baseline:                      # first look: remember, don't alarm
        st.baseline = True
        watch.log_event(f"baseline {len(known)} devices")
    else:
        for e in events:
            st.events.appendleft(GuardEvent(time.time(), e))
            _title, text = watch.describe(e, "en")
            watch.log_event(f"{e.kind} {text}")
            watch.notify(*watch.describe(e, "ro"))
    st.status = "waiting"


def _loop(net: netdetect.NetworkInfo, st: GuardState) -> None:
    try:
        while not _stop.is_set():
            try:
                run_cycle(net, st)
                st.message = ""
            except Exception as e:  # keep guarding; show the reason
                st.status, st.message = "error", f"{e.__class__.__name__}: {e}"[:300]
            _stop.wait(st.interval)
    finally:
        st.running = st.stopping = False
        st.status = "idle"
