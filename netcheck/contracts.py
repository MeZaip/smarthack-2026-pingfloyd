"""Inter-module JSON payloads, exactly as defined in service_data_contracts.md.

  §1 Raw Parsed Data      (Core CLI -> Rule Engine)   raw_scan(), raw_from_file(), hosts_from_raw()
  §2 Evaluated Scan Data  (Rule Engine -> UI / DB)    evaluated_scan()
  §4 History & Deltas     (Database -> UI)            delta()
(§3, the LLM enrichment payload, belongs to the LLM service.)

Conventions where the contract is silent (documented in service_data_contracts.md, "CLI notes"):
  * unknown strings (vendor, hostname, version, banner, gateway, timestamp) are null, never "";
  * TLS-wrapped services use nmap's own notation "ssl/<name>" in `service` (e.g. "ssl/http"),
    so the Rule Engine can tell HTTPS from plain HTTP (needed for HTTP_ADMIN_CLEARTEXT);
  * `version` = nmap product + version ("OpenSSH 7.9p1"), split back by hosts_from_raw();
  * an unreadable file in §2 gets "network_score": null plus an "error" message.
"""
from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from pathlib import Path

from .models import Host, Port, ScanResult
from .models import mask_mac as _mask_mac
from .parser import ScanMeta, parse_scan, read_file

MAX_STR = 500
_VERSION_TOKEN = re.compile(r"^\d+(\.|$)")


class ContractError(ValueError):
    """Payload does not follow the data contract. Message is user-facing."""


# ------------------------------------------------------------------ helpers
def mask_mac(mac: str) -> str | None:
    """Contract format 'XX:XX:XX:XX:1A:2B' (same rule as models.mask_mac); unknown MAC -> null."""
    return _mask_mac(mac) or None


def _null(s: str | None) -> str | None:
    return s if s else None


def scan_id(file_name: str) -> str:
    return Path(file_name).stem


def iso_utc(unix: int | None) -> str | None:
    if unix is None:
        return None
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def infer_subnet(meta: ScanMeta, hosts: list[Host]) -> str | None:
    """Offline files: the target in the nmap command line, else the /24 shared by all hosts."""
    for tok in reversed(meta.args.split()):
        try:
            net = ipaddress.ip_network(tok, strict=False)
        except ValueError:
            continue
        if net.prefixlen < net.max_prefixlen:
            return str(net)
    nets = set()
    for h in hosts:
        try:
            nets.add(ipaddress.ip_network(f"{h.ip}/24", strict=False))
        except ValueError:
            return None
    return str(nets.pop()) if len(nets) == 1 else None


def _service(p: Port) -> str | None:
    if not p.service:
        return None
    return f"ssl/{p.service}" if p.tunnel == "ssl" else p.service


def _banner(p: Port) -> str | None:
    parts = ([f"title: {p.title}"] if p.title else []) + ([p.banner] if p.banner else [])
    return " | ".join(parts)[:MAX_STR] or None


def _type_guess(h: Host) -> str:
    from .analyzer import guess_type  # deferred: analyzer imports parser too
    return guess_type(h)


# ------------------------------------------------------------------ §1 Raw Parsed Data
def raw_scan(hosts: list[Host], sid: str, timestamp: str | None, subnet: str | None,
             gateway: str | None) -> dict:
    return {
        "scan_id": sid,
        "timestamp": timestamp,
        "network": {"subnet": subnet, "gateway": gateway},
        "devices": [{
            "ip": h.ip,
            "mac_masked": mask_mac(h.mac),
            "vendor": _null(h.vendor),
            "hostname": _null(h.hostname),
            "device_type_guess": _type_guess(h),
            "open_ports": [{
                "port": p.portid,
                "protocol": p.protocol,
                "service": _service(p),
                "version": " ".join(x for x in (p.product, p.version) if x) or None,
                "evidence_banner": _banner(p),
            } for p in sorted(h.open_ports, key=lambda p: (p.protocol, p.portid))],
        } for h in hosts],
    }


def raw_from_file(path, gateway: str | None = None, subnet: str | None = None) -> dict:
    """nmap XML file -> §1 payload. Raises parser.ScanFileError for unreadable files."""
    hosts, meta = parse_scan(read_file(path))
    return raw_scan(hosts, scan_id(Path(path).name), iso_utc(meta.start),
                    subnet or infer_subnet(meta, hosts), gateway)


def _s(v, field: str) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        raise ContractError(f"{field} must be a string or null")
    return v.strip()[:MAX_STR]


def _split_version(v: str) -> tuple[str, str]:
    toks = v.split()
    for i, t in enumerate(toks):
        if _VERSION_TOKEN.match(t):
            return " ".join(toks[:i]), " ".join(toks[i:])
    return v, ""


def hosts_from_raw(payload) -> list[Host]:
    """§1 payload -> Host objects for the Rule Engine. The payload is treated as hostile input."""
    if not isinstance(payload, dict) or not isinstance(payload.get("devices"), list):
        raise ContractError("payload must be an object with a 'devices' list")
    hosts = []
    for i, d in enumerate(payload["devices"]):
        if not isinstance(d, dict):
            raise ContractError(f"devices[{i}] must be an object")
        ip = _s(d.get("ip"), f"devices[{i}].ip")
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ContractError(f"devices[{i}].ip is not an IP address") from None
        ports = []
        for j, p in enumerate(d.get("open_ports") or []):
            where = f"devices[{i}].open_ports[{j}]"
            if not isinstance(p, dict):
                raise ContractError(f"{where} must be an object")
            num = p.get("port")
            if not isinstance(num, int) or isinstance(num, bool) or not 0 < num < 65536:
                raise ContractError(f"{where}.port must be an integer 1-65535")
            proto = _s(p.get("protocol"), f"{where}.protocol").lower()
            if proto not in ("tcp", "udp"):
                raise ContractError(f"{where}.protocol must be 'tcp' or 'udp'")
            svc = _s(p.get("service"), f"{where}.service").lower()
            tunnel = ""
            if svc.startswith("ssl/"):
                svc, tunnel = svc[4:], "ssl"
            product, version = _split_version(_s(p.get("version"), f"{where}.version"))
            banner = _s(p.get("evidence_banner"), f"{where}.evidence_banner")
            title = ""
            if banner.startswith("title: "):
                title = banner[7:].split(" | ")[0]
            ports.append(Port(protocol=proto, portid=num, state="open", service=svc, product=product,
                              version=version, tunnel=tunnel, title=title, banner=banner))
        hosts.append(Host(ip=ip, vendor=_s(d.get("vendor"), "vendor"),
                          hostname=_s(d.get("hostname"), "hostname"), ports=ports))
    return hosts


# ------------------------------------------------------------------ §2 Evaluated Scan Data
def evaluated_scan(result: ScanResult, hosts: list[Host] | None = None) -> dict:
    """ScanResult (+ the parsed hosts, for contract-format MACs) -> §2 payload."""
    if not result.ok:
        return {"scan_id": scan_id(result.file), "network_score": None, "error": result.error,
                "devices": [], "findings": []}
    macs = {h.ip: h.mac for h in hosts or []}

    def masked(d) -> str | None:
        return mask_mac(macs[d.ip]) if d.ip in macs else (d.mac_masked or None)

    return {
        "scan_id": scan_id(result.file),
        "network_score": result.score,
        "devices": [{
            "ip": d.ip,
            "mac_masked": masked(d),
            "vendor": _null(d.vendor),
            "hostname": _null(d.hostname),
            "device_type_guess": d.type_guess,
        } for d in result.devices],
        "findings": [{
            "ip": f.ip,
            "port": f.port,
            "finding_code": f.code,
            "severity": f.severity,
            "points": f.points,
            "evidence": f.evidence,
        } for f in result.findings],
    }


# ------------------------------------------------------------------ §4 History & Deltas
def delta(previous: ScanResult, current: ScanResult, previous_hosts: list[Host] | None = None,
          current_hosts: list[Host] | None = None) -> dict:
    from .history import diff  # reuse the Data Layer's comparison logic
    d = diff(previous, current)
    macs = {h.ip: h.mac for h in (previous_hosts or []) + (current_hosts or [])}

    def dev(x):
        m = mask_mac(macs[x["ip"]]) if x["ip"] in macs else (x.get("mac_masked") or None)
        return {"ip": x["ip"], "mac_masked": m}

    def fnd(x):
        return {"ip": x["ip"], "port": x["port"], "finding_code": x["code"]}

    return {
        "current_scan_id": scan_id(current.file),
        "previous_scan_id": scan_id(previous.file),
        "score_trend": {
            "previous_score": previous.score,
            "current_score": current.score,
            "improved": (current.score or 0) > (previous.score or 0),
        },
        "deltas": {
            "new_devices": [dev(x) for x in d["new_devices"]],
            "removed_devices": [dev(x) for x in d["removed_devices"]],
            "new_findings": [fnd(x) for x in d["new_findings"]],
            "resolved_findings": [fnd(x) for x in d["resolved_findings"]],
        },
    }
