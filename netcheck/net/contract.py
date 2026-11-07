"""service_data_contracts.md §1 — Raw Parsed Data (Core CLI ➔ Rule Engine).

raw_scan()       core.models.ScanResult -> §1 JSON dict
hosts_from_raw() §1 JSON dict -> core.models.Host list (hostile input, validated) for core.rules

Conventions where the contract is silent (see the appendix in service_data_contracts.md):
  * unknown values are null, never "";
  * TLS-wrapped services use nmap's notation "ssl/<name>" (e.g. "ssl/http"), otherwise the
    Rule Engine would mistake HTTPS for plain HTTP (HTTP_ADMIN_CLEARTEXT trap in V1/V5);
  * "version" = nmap product + version ("OpenSSH 7.9p1"); split back at the first token
    that starts with a digit;
  * "evidence_banner" = "title: <http-title>" then other script outputs as "<id>: <output>", joined by " | ";
  * "timestamp" = nmaprun@start in UTC (deterministic); "gateway" is only known during a live scan.
"""
from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from pathlib import Path

from ..core.device import guess_type
from ..core.models import Host, Port, ScanResult

MAX_STR = 500
_VERSION_TOKEN = re.compile(r"^\d+(\.|$)")


class ContractError(ValueError):
    """Payload does not follow the data contract. Message is user-facing."""


def mask_mac(mac: str | None) -> str | None:
    """Contract format: only the last two bytes stay visible -> 'XX:XX:XX:XX:1A:2B'."""
    if not mac:
        return None
    parts = mac.replace("-", ":").upper().split(":")
    if len(parts) != 6 or not all(re.fullmatch(r"[0-9A-F]{1,2}", p) for p in parts):
        return "XX:XX:XX:XX:XX:XX"
    return ":".join(["XX"] * 4 + [p.zfill(2) for p in parts[4:]])


def iso_utc(unix: int | None) -> str | None:
    if unix is None:
        return None
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def infer_subnet(scan: ScanResult) -> str | None:
    """Offline files: the target in the nmap command line, else the /24 shared by all hosts."""
    for tok in reversed(scan.args.split()):
        try:
            net = ipaddress.ip_network(tok, strict=False)
        except ValueError:
            continue
        if net.prefixlen < net.max_prefixlen:
            return str(net)
    nets = set()
    for h in scan.hosts:
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
    parts = [f"title: {p.http_title}"] if p.http_title else []
    parts += [f"{sid}: {out}" for sid, out in sorted(p.scripts.items()) if sid != "http-title" and out]
    return " | ".join(parts)[:MAX_STR] or None


def raw_scan(scan: ScanResult, subnet: str | None = None, gateway: str | None = None) -> dict:
    return {
        "scan_id": Path(scan.source).stem,
        "timestamp": iso_utc(scan.start_time),
        "network": {"subnet": subnet or infer_subnet(scan), "gateway": gateway or None},
        "devices": [{
            "ip": h.ip,
            "mac_masked": mask_mac(h.mac),
            "vendor": h.vendor or None,
            "hostname": h.hostname or None,
            "device_type_guess": guess_type(h, is_gateway=bool(gateway) and h.ip == gateway),
            "open_ports": [{
                "port": p.portid,
                "protocol": p.protocol,
                "service": _service(p),
                "version": " ".join(x for x in (p.product, p.version) if x) or None,
                "evidence_banner": _banner(p),
            } for p in sorted(h.open_ports, key=lambda p: (p.protocol, p.portid))],
        } for h in scan.up_hosts],
    }


# ------------------------------------------------------------------ reading §1 back (hostile input)
def _s(v, field: str) -> str:
    if v is None:
        return ""
    if not isinstance(v, str):
        raise ContractError(f"{field} must be a string or null")
    return v.replace("\x00", "").strip()[:MAX_STR]


def _split_version(v: str) -> tuple[str, str]:
    toks = v.split()
    for i, t in enumerate(toks):
        if _VERSION_TOKEN.match(t):
            return " ".join(toks[:i]), " ".join(toks[i:])
    return v, ""


def _scripts(banner: str) -> dict[str, str]:
    out = {}
    for part in banner.split(" | ") if banner else []:
        sid, sep, text = part.partition(": ")
        if sep:
            out["http-title" if sid == "title" else sid] = text
    return out


def hosts_from_raw(payload) -> list[Host]:
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
            ports.append(Port(protocol=proto, portid=num, state="open", service=svc, product=product,
                              version=version, tunnel=tunnel,
                              scripts=_scripts(_s(p.get("evidence_banner"), f"{where}.evidence_banner"))))
        hostname = _s(d.get("hostname"), "hostname")
        hosts.append(Host(ip=ip, status="up", vendor=_s(d.get("vendor"), "vendor") or None,
                          hostnames=[hostname] if hostname else [], ports=ports))
    return hosts
