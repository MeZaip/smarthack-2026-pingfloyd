"""High-level analysis of one file or a whole folder + standard CSV export (FR-05, FR-15)."""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .device import guess_type, mask_mac
from .models import Finding, ScanResult
from .parser import ScanFileError, parse_file
from .rules import device_risk, evaluate, network_score, prioritized


@dataclass
class Analysis:
    file: str
    scan: Optional[ScanResult] = None
    findings: list[Finding] = field(default_factory=list)
    score: Optional[int] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def devices(self) -> list[dict]:
        """Device list for UI / AI tools. MAC is always masked."""
        if not self.scan:
            return []
        risk = device_risk(self.findings)
        out = []
        for h in self.scan.up_hosts:
            out.append({
                "ip": h.ip,
                "mac": mask_mac(h.mac),
                "vendor": h.vendor,
                "hostname": h.hostname,
                "type": guess_type(h),
                "open_ports": [
                    {"port": p.portid, "protocol": p.protocol, "service": p.service,
                     "product": p.product, "version": p.version,
                     "tls": p.tunnel == "ssl", "title": p.http_title or None}
                    for p in h.open_ports
                ],
                "risk_points": risk.get(h.ip, 0),
                "findings": [f.code for f in self.findings if f.ip == h.ip],
            })
        out.sort(key=lambda d: -d["risk_points"])
        return out

    def most_dangerous(self) -> Optional[dict]:
        devs = [d for d in self.devices() if d["risk_points"] > 0]
        return devs[0] if devs else None

    def prioritized(self) -> list[Finding]:
        return prioritized(self.findings)


def analyze_file(path: str | os.PathLike) -> Analysis:
    name = Path(path).name
    try:
        scan = parse_file(path)
    except ScanFileError as e:
        return Analysis(file=name, error=str(e))
    except Exception as e:  # never crash on a single bad file
        return Analysis(file=name, error=f"unexpected error: {e.__class__.__name__}")
    findings = evaluate(scan)
    return Analysis(file=name, scan=scan, findings=findings, score=network_score(findings))


def scan_files_in(folder: str | os.PathLike, all_files: bool = False) -> list[Path]:
    """Scan files of a folder, by name. Default: *.xml. all_files=True: every non-hidden file, so an
    unreadable file with another extension still gets its ERROR row in scores.csv."""
    p = Path(folder)
    if p.is_file():
        return [p]
    return sorted((f for f in p.iterdir() if f.is_file() and not f.name.startswith(".")
                   and (all_files or f.suffix.lower() == ".xml")), key=lambda f: f.name)


def skipped_files_in(folder: str | os.PathLike) -> list[str]:
    """Non-hidden files that the default (*.xml) analysis does not read - shown as a warning."""
    p = Path(folder)
    if p.is_file():
        return []
    return sorted(f.name for f in p.iterdir() if f.is_file() and not f.name.startswith(".")
                  and f.suffix.lower() != ".xml")


def analyze_folder(folder: str | os.PathLike, all_files: bool = False) -> list[Analysis]:
    return [analyze_file(f) for f in scan_files_in(folder, all_files)]


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection in any cell we write."""
    s = "" if value is None else str(value)
    if s and s[0] in "=+-@\t\r":
        s = "'" + s
    return s


def write_results(results: list[Analysis], out_dir: str | os.PathLike) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    findings_path = out / "findings.csv"
    scores_path = out / "scores.csv"
    with findings_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["file", "ip", "port", "finding_code", "severity"])
        for r in results:
            for f in r.findings:
                w.writerow([_csv_safe(r.file), f.ip, "" if f.port is None else f.port, f.code, f.severity])
    with scores_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["file", "network_score"])
        for r in results:
            w.writerow([_csv_safe(r.file), "ERROR" if not r.ok else r.score])
    return findings_path, scores_path
