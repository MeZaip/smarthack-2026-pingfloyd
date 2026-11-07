from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Port:
    protocol: str            # "tcp" | "udp"
    portid: int
    state: str               # "open", "closed", "filtered", "open|filtered", ...
    service: str = ""        # nmap service name, lower-case ("http", "ssh", ...)
    product: str = ""
    version: str = ""
    extrainfo: str = ""
    tunnel: str = ""         # "ssl" when nmap detected TLS wrapping
    scripts: dict[str, str] = field(default_factory=dict)  # script id -> output (untrusted text)

    @property
    def is_open(self) -> bool:
        return self.state == "open"

    @property
    def http_title(self) -> str:
        return self.scripts.get("http-title", "")


@dataclass
class Host:
    ip: str
    status: str = "up"
    mac: Optional[str] = None
    vendor: Optional[str] = None
    hostnames: list[str] = field(default_factory=list)
    os_guess: Optional[str] = None
    ports: list[Port] = field(default_factory=list)

    @property
    def open_ports(self) -> list[Port]:
        return [p for p in self.ports if p.is_open]

    @property
    def hostname(self) -> Optional[str]:
        return self.hostnames[0] if self.hostnames else None


@dataclass
class ScanResult:
    source: str                       # file name (no directory)
    hosts: list[Host]
    start_time: Optional[int] = None  # unix timestamp from nmaprun/@start
    args: str = ""

    @property
    def up_hosts(self) -> list[Host]:
        return [h for h in self.hosts if h.status == "up"]


@dataclass(frozen=True)
class Finding:
    ip: str
    port: Optional[int]       # None for device-level findings (UNKNOWN_DEVICE)
    protocol: Optional[str]
    code: str
    severity: str             # "high" | "medium" | "low" | "info"
    points: int
    evidence: str             # short, factual, derived from the scan only

    @property
    def sort_key(self):
        return (_ip_key(self.ip), self.port if self.port is not None else -1, self.code)


def _ip_key(ip: str):
    import ipaddress
    try:
        a = ipaddress.ip_address(ip)
        return (a.version, int(a))
    except ValueError:
        return (9, ip)
