"""Difference between two scans of the same network (FR-10, FR-13).

The comparison works on a `Snapshot`, so the same logic serves two sources:
two XML files analysed now (`compare`) and two scans read back from the
local history database (`netcheck.history`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .analysis import Analysis
from .models import Host

PortKey = tuple  # (ip, protocol, port, service, tls)
FindingKey = tuple  # (ip, port, code)


@dataclass(frozen=True)
class Snapshot:
    file: str
    score: int
    devices: dict            # device_key -> ip
    open_ports: frozenset    # of PortKey
    findings: frozenset      # of FindingKey


def device_key(host: Host) -> str:
    # MAC is the stable identity when we have it (IPs can change via DHCP)
    return (host.mac or "").upper() or f"ip:{host.ip}"


def snapshot_of(a: Analysis, key_fn: Callable[[Host], str] = device_key) -> Snapshot:
    if not a.ok:
        raise ValueError(f"{a.file} is not readable: {a.error}")
    hosts = a.scan.up_hosts
    return Snapshot(
        file=a.file,
        score=a.score,
        devices={key_fn(h): h.ip for h in hosts},
        open_ports=frozenset((h.ip, p.protocol, p.portid, p.service, p.tunnel == "ssl")
                             for h in hosts for p in h.open_ports),
        findings=frozenset((f.ip, f.port, f.code) for f in a.findings),
    )


def _port_dicts(keys) -> list[dict]:
    return [{"ip": i, "protocol": pr, "port": po, "service": s, "tls": tls} for i, pr, po, s, tls in sorted(keys)]


# Cleartext service -> services that replace it securely (besides the same service over TLS).
_SECURE_REPLACEMENT = {"telnet": {"ssh"}, "ftp": {"sftp", "ssh", "ftps"}}


def _upgrades(opened: frozenset, closed: frozenset) -> list[dict]:
    """Opened ports that are the secure replacement of a cleartext port closed on the same device,
    e.g. router admin moved from http/80 to https/443. These are fixes, not new risks."""
    out = []
    for ip, pr, po, svc, tls in sorted(opened):
        for c_ip, c_pr, c_po, c_svc, c_tls in sorted(closed):
            if c_ip != ip or c_tls:
                continue
            if (tls and svc == c_svc) or svc in _SECURE_REPLACEMENT.get(c_svc, ()):
                out.append({"ip": ip, "service": svc, "from_port": c_po, "to_port": po, "protocol": pr})
                break
    return out


def _finding_dicts(keys) -> list[dict]:
    return [{"ip": i, "port": p, "code": c} for i, p, c in sorted(keys, key=str)]


def _device_changes(before: Snapshot, after: Snapshot) -> tuple[list[str], list[str]]:
    """New / removed devices. Identity is the MAC (IPs change with DHCP), but phones and laptops now
    use private MAC addresses that can change between scans: a device that keeps its IP while its
    MAC changes is the same device with a new private address, not "one gone + one new"."""
    b_only = {k: ip for k, ip in before.devices.items() if k not in after.devices}
    a_only = {k: ip for k, ip in after.devices.items() if k not in before.devices}
    b_ips, a_ips = set(b_only.values()), set(a_only.values())
    new = sorted(ip for ip in a_only.values() if ip not in b_ips)
    removed = sorted(ip for ip in b_only.values() if ip not in a_ips)
    return new, removed


def compare_snapshots(before: Snapshot, after: Snapshot) -> dict:
    new_devices, removed_devices = _device_changes(before, after)
    opened = after.open_ports - before.open_ports
    closed = before.open_ports - after.open_ports
    upgraded = _upgrades(opened, closed)
    upgraded_keys = {(u["ip"], u["protocol"], u["to_port"]) for u in upgraded}
    alert_ports = frozenset(k for k in opened if (k[0], k[1], k[2]) not in upgraded_keys)
    return {
        "before_file": before.file,
        "after_file": after.file,
        "score_before": before.score,
        "score_after": after.score,
        "score_change": after.score - before.score,
        "new_devices": new_devices,
        "removed_devices": removed_devices,
        "opened_ports": _port_dicts(opened),
        "closed_ports": _port_dicts(closed),
        "secured_ports": upgraded,                 # opened ports that replace a closed cleartext one
        "new_port_alerts": _port_dicts(alert_ports),
        "resolved_findings": _finding_dicts(before.findings - after.findings),
        "new_findings": _finding_dicts(after.findings - before.findings),
        "alerts": bool(new_devices or alert_ports),
    }


def compare(before: Analysis, after: Analysis) -> dict:
    if not (before.ok and after.ok):
        raise ValueError("both analyses must be readable")
    return compare_snapshots(snapshot_of(before), snapshot_of(after))
