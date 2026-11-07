"""File -> ScanResult pipeline, standard score, device-type guess, CSV export."""
from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path

from .identity import device_id
from .models import Device, Finding, Host, ScanResult
from .parser import ScanFileError, parse_bytes, read_file
from .rules import SEVERITY_ORDER, _ip_key, classify


def standard_score(findings: list[Finding]) -> int:
    """Official formula (FR-09): max(0, 100 - sum of points)."""
    return max(0, 100 - sum(f.points for f in findings))


_TYPE_HINTS = [
    ("camera", ("hikvision", "dahua", "axis", "reolink", "foscam", "ezviz", "amcrest", "camera", "ipcam")),
    ("printer", ("hp", "hewlett", "canon", "epson", "brother", "xerox", "lexmark", "kyocera", "printer")),
    ("router", ("tp-link", "tplink", "netgear", "asus", "zyxel", "d-link", "mikrotik", "ubiquiti",
                "huawei", "router", "gateway", "fritz", "linksys", "technicolor", "sagemcom")),
    ("nas", ("synology", "qnap", "western digital", "nas", "diskstation")),
    ("tv / media", ("samsung electronics", "lg electronics", "sony", "roku", "chromecast", "google", "tv", "vizio")),
    ("iot / smart home", ("espressif", "tuya", "shelly", "sonoff", "philips lighting", "hub", "iot", "raspberry")),
    ("phone / tablet", ("apple", "iphone", "ipad", "android", "xiaomi", "oneplus", "oppo", "phone", "galaxy")),
    ("computer", ("dell", "lenovo", "intel", "microsoft", "desktop", "laptop", "macbook", "pc", "vmware", "virtualbox")),
]


def guess_type(host: Host) -> str:
    services = {p.service for p in host.open_ports}
    if "rtsp" in services:
        return "camera"
    if "jetdirect" in services or "ipp" in services:
        return "printer"
    if "ms-wbt-server" in services:
        return "computer"
    text = f"{host.vendor} {host.hostname}".lower()
    for kind, words in _TYPE_HINTS:
        if any(w in text for w in words):
            return kind
    if services & {"upnp", "domain"} and host.ip.endswith(".1"):
        return "router"
    if services & {"mysql", "postgresql", "redis", "mongodb", "ssh"}:
        return "server"
    return "unknown"


def build_devices(hosts: list[Host], findings: list[Finding]) -> list[Device]:
    pts: dict[str, int] = {}
    for f in findings:
        pts[f.ip] = pts.get(f.ip, 0) + f.points
    devices = []
    for h in hosts:
        devices.append(Device(
            ip=h.ip,
            mac_masked=h.mac_masked,
            vendor=h.vendor,
            hostname=h.hostname,
            type_guess=guess_type(h),
            open_ports=[{
                "port": p.portid, "protocol": p.protocol, "service": p.service,
                "product": p.product, "version": p.version, "tunnel": p.tunnel, "title": p.title,
            } for p in sorted(h.open_ports, key=lambda p: (p.protocol, p.portid))],
            risk_points=pts.get(h.ip, 0),
            device_id=device_id(h.mac, h.ip),
        ))
    return sorted(devices, key=lambda d: _ip_key(d.ip))


def analyze_file(path: str | os.PathLike, display_name: str | None = None) -> ScanResult:
    name = display_name or Path(path).name
    try:
        data = read_file(path)
    except ScanFileError as e:
        return ScanResult(file=name, ok=False, error=str(e))
    return analyze_bytes(data, name)


def analyze_bytes(data: bytes, name: str) -> ScanResult:
    sha = hashlib.sha256(data).hexdigest()
    try:
        hosts = parse_bytes(data)
    except ScanFileError as e:
        return ScanResult(file=name, ok=False, error=str(e), file_sha256=sha)
    except Exception as e:  # never crash the batch on one bad file
        return ScanResult(file=name, ok=False, error=f"unexpected error while reading: {type(e).__name__}",
                          file_sha256=sha)
    findings = classify(name, hosts)
    return ScanResult(
        file=name, ok=True,
        devices=build_devices(hosts, findings),
        findings=findings,
        score=standard_score(findings),
        file_sha256=sha,
    )


def list_scan_files(folder: str | os.PathLike, all_files: bool = False) -> list[Path]:
    folder = Path(folder)
    files = [p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not all_files:
        files = [p for p in files if p.suffix.lower() == ".xml"]
    return sorted(files, key=lambda p: p.name)


def analyze_folder(folder: str | os.PathLike, all_files: bool = False) -> list[ScanResult]:
    return [analyze_file(p) for p in list_scan_files(folder, all_files)]


def write_csvs(results: list[ScanResult], out_dir: str | os.PathLike) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fpath, spath = out / "findings.csv", out / "scores.csv"
    with fpath.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["file", "ip", "port", "finding_code", "severity"])
        for r in results:
            for f in r.findings:
                w.writerow([f.file, f.ip, "" if f.port is None else f.port, f.code, f.severity])
    with spath.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["file", "network_score"])
        for r in results:
            w.writerow([r.file, r.score_str])
    return fpath, spath


def most_dangerous(result: ScanResult) -> tuple[Device | None, Finding | None]:
    """Device with most risk points; its worst finding is 'fix this first'."""
    if not result.ok or not result.findings:
        return None, None
    risky = [d for d in result.devices if d.risk_points > 0]
    if not risky:
        return None, None
    dev = sorted(risky, key=lambda d: (-d.risk_points, _ip_key(d.ip)))[0]
    worst = sorted(
        [f for f in result.findings if f.ip == dev.ip],
        key=lambda f: (-f.points, SEVERITY_ORDER[f.severity], -1 if f.port is None else f.port),
    )[0]
    return dev, worst


def ranked_findings(result: ScanResult) -> list[Finding]:
    return sorted(result.findings, key=lambda f: (-f.points, SEVERITY_ORDER[f.severity], _ip_key(f.ip),
                                                  -1 if f.port is None else f.port))
