"""Live scan started from the web UI (FR-02/04 through the browser).

The web process stays unprivileged (NFR-04): only nmap runs through `sudo -n` (never prompts).
Every target goes through net/guardrail.py exactly like `netcheck scan`; the UI cannot widen the
allowlist (only NETCHECK_ALLOWLIST on this machine can). One scan at a time, in a background thread,
because a /24 with top-1000 TCP + UDP takes minutes.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..core.analysis import Analysis, analyze_file
from ..core.parser import ScanFileError, parse_file
from ..net import contract, guardrail, netdetect, scanner


class Busy(Exception):
    pass


@dataclass
class Job:
    target: str
    started: float
    state: str = "running"          # running | done | error | needs_root
    finished: Optional[float] = None
    scan_id: Optional[int] = None
    score: Optional[int] = None
    findings: int = 0
    file: str = ""
    message: str = ""               # technical detail for errors (already escaped by Jinja)

    @property
    def elapsed(self) -> int:
        return int((self.finished or time.time()) - self.started)


_lock = threading.Lock()
_job: Optional[Job] = None


def scans_dir() -> Path:
    return Path(os.environ.get("NETCHECK_SCANS_DIR", "scans"))


def current() -> Optional[Job]:
    return _job


def reset() -> None:  # tests
    global _job
    with _lock:
        _job = None


def detect() -> netdetect.NetworkInfo:
    return netdetect.detect()


def check(target: str | None, confirmed: bool) -> tuple[netdetect.NetworkInfo, str]:
    """Detect the network and validate the target. Raises ScopeError / NetworkDetectError."""
    net = detect()
    allow = guardrail.build_allowlist(net.subnet)          # no extra ranges from the browser
    return net, guardrail.check_target((target or "").strip() or net.subnet, allow, confirmed=confirmed)


def start(net: netdetect.NetworkInfo, target: str, save: Callable[[Analysis], int]) -> Job:
    """Start the scan in the background. `save` stores the analysis and returns its history id."""
    global _job
    with _lock:
        if _job and _job.state == "running":
            raise Busy(_job.target)
        _job = Job(target=target, started=time.time())
        job = _job
    threading.Thread(target=_run, args=(job, net, save), daemon=True, name="netcheck-live-scan").start()
    return job


def _run(job: Job, net: netdetect.NetworkInfo, save: Callable[[Analysis], int]) -> None:
    try:
        xml = scanner.run_scan(job.target, scans_dir(), interactive=False)
        try:  # §1 with the live network facts, like `netcheck scan`
            raw = contract.raw_scan(parse_file(xml), net.subnet, net.gateway)
            xml.with_suffix(".raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8")
        except ScanFileError:
            pass
        a = analyze_file(xml)
        job.file = xml.name
        if not a.ok:
            job.state, job.message = "error", a.error or ""
        else:
            job.scan_id = save(a)
            job.score, job.findings, job.state = a.score, len(a.findings), "done"
    except scanner.NeedsRootError as e:
        job.state, job.message = "needs_root", str(e)
    except Exception as e:  # never kill the server; show the reason
        job.state, job.message = "error", f"{e.__class__.__name__}: {e}"[:400]
    finally:
        job.finished = time.time()
