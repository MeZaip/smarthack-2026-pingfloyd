"""Shared data contract. Every module (parser, rules, UI, chat) speaks these types."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Port:
    protocol: str            # "tcp" | "udp"
    portid: int
    state: str               # "open", "filtered", "open|filtered", ...
    service: str = ""        # nmap service name, lower-case ("http", "ssh", ...)
    product: str = ""
    version: str = ""
    extrainfo: str = ""
    tunnel: str = ""         # "ssl" when nmap detected TLS
    title: str = ""          # http-title script output, if any
    banner: str = ""         # any other script output (untrusted text)


@dataclass
class Host:
    ip: str
    mac: str = ""            # raw MAC, NEVER written to output; use mac_masked
    vendor: str = ""
    hostname: str = ""
    ports: list[Port] = field(default_factory=list)

    @property
    def mac_masked(self) -> str:
        return mask_mac(self.mac)

    @property
    def open_ports(self) -> list[Port]:
        return [p for p in self.ports if p.state == "open"]


@dataclass
class Finding:
    file: str
    ip: str
    port: Optional[int]      # None for UNKNOWN_DEVICE
    code: str
    severity: str            # high | medium | low | info
    points: int
    protocol: str = ""
    service: str = ""
    product: str = ""
    version: str = ""
    evidence: str = ""       # human-readable proof taken from the scan

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Device:
    ip: str
    mac_masked: str
    vendor: str
    hostname: str
    type_guess: str
    open_ports: list[dict]
    risk_points: int = 0
    device_id: str = ""      # HMAC of the MAC with a local secret (see identity.py)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanResult:
    file: str
    ok: bool
    error: str = ""
    devices: list[Device] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    score: Optional[int] = None
    file_sha256: str = ""    # fingerprint of the exact scan file analysed

    @property
    def score_str(self) -> str:
        return "ERROR" if not self.ok or self.score is None else str(self.score)

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "ok": self.ok,
            "error": self.error,
            "score": self.score,
            "file_sha256": self.file_sha256,
            "devices": [d.to_dict() for d in self.devices],
            "findings": [f.to_dict() for f in self.findings],
        }

    @staticmethod
    def from_dict(d: dict) -> "ScanResult":
        return ScanResult(
            file=d["file"],
            ok=d["ok"],
            error=d.get("error", ""),
            score=d.get("score"),
            file_sha256=d.get("file_sha256", ""),
            devices=[Device(**x) for x in d.get("devices", [])],
            findings=[Finding(**x) for x in d.get("findings", [])],
        )


def mask_mac(mac: str) -> str:
    """The single MAC-masking rule (service_data_contracts.md): only the last two bytes stay
    visible -> 'XX:XX:XX:XX:1A:2B'. The manufacturer is already shown via `vendor`."""
    if not mac:
        return ""
    parts = mac.replace("-", ":").upper().split(":")
    if len(parts) != 6 or not all(re.fullmatch(r"[0-9A-F]{1,2}", p) for p in parts):
        return "XX:XX:XX:XX:XX:XX"
    return ":".join(["XX"] * 4 + [p.zfill(2) for p in parts[4:]])
