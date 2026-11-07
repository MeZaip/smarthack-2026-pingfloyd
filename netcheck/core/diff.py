"""Difference between two analyses of the same network (FR-10, FR-13)."""
from __future__ import annotations

from .analysis import Analysis


def _device_key(host) -> str:
    # MAC is the stable identity when we have it (IPs can change via DHCP)
    return (host.mac or "").upper() or f"ip:{host.ip}"


def compare(before: Analysis, after: Analysis) -> dict:
    if not (before.ok and after.ok):
        raise ValueError("both analyses must be readable")
    b_hosts = {_device_key(h): h for h in before.scan.up_hosts}
    a_hosts = {_device_key(h): h for h in after.scan.up_hosts}

    new_devices = sorted(a_hosts[k].ip for k in a_hosts.keys() - b_hosts.keys())
    removed_devices = sorted(b_hosts[k].ip for k in b_hosts.keys() - a_hosts.keys())

    def open_set(hosts):
        return {(h.ip, p.protocol, p.portid, p.service) for h in hosts.values() for p in h.open_ports}

    b_open, a_open = open_set(b_hosts), open_set(a_hosts)
    opened = sorted(a_open - b_open)
    closed = sorted(b_open - a_open)

    fkey = lambda f: (f.ip, f.port, f.code)
    b_f = {fkey(f): f for f in before.findings}
    a_f = {fkey(f): f for f in after.findings}
    resolved = [b_f[k] for k in sorted(b_f.keys() - a_f.keys(), key=str)]
    new_findings = [a_f[k] for k in sorted(a_f.keys() - b_f.keys(), key=str)]

    return {
        "before_file": before.file,
        "after_file": after.file,
        "score_before": before.score,
        "score_after": after.score,
        "score_change": after.score - before.score,
        "new_devices": new_devices,
        "removed_devices": removed_devices,
        "opened_ports": [{"ip": i, "protocol": pr, "port": po, "service": s} for i, pr, po, s in opened],
        "closed_ports": [{"ip": i, "protocol": pr, "port": po, "service": s} for i, pr, po, s in closed],
        "resolved_findings": [{"ip": f.ip, "port": f.port, "code": f.code} for f in resolved],
        "new_findings": [{"ip": f.ip, "port": f.port, "code": f.code} for f in new_findings],
        "alerts": bool(new_devices or opened),
    }
