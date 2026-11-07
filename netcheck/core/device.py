"""Device presentation helpers: MAC masking (NFR-02) and a device-type guess (FR-03)."""
from __future__ import annotations

from typing import Optional

from .models import Host


def mask_mac(mac: Optional[str]) -> Optional[str]:
    """Keep the vendor prefix (OUI), hide the device-specific half: AA:BB:CC:XX:XX:XX."""
    if not mac:
        return None
    parts = mac.replace("-", ":").upper().split(":")
    if len(parts) != 6:
        return "XX:XX:XX:XX:XX:XX"
    return ":".join(parts[:3] + ["XX"] * 3)


_VENDOR_HINTS = [
    (("tp-link", "netgear", "zte", "huawei", "asus", "mikrotik", "ubiquiti", "d-link", "linksys", "fritz", "avm"), "router"),
    (("hikvision", "dahua", "axis", "reolink", "wyze", "ezviz"), "camera"),
    (("hewlett", "hp inc", "brother", "canon", "epson", "lexmark", "xerox", "kyocera", "ricoh"), "printer"),
    (("synology", "qnap", "western digital"), "nas"),
    (("raspberry", "espressif", "tuya", "shelly", "sonoff", "philips lighting", "signify"), "iot"),
    (("samsung", "lg electronics", "sony", "roku", "tcl", "hisense", "vizio"), "tv"),
    (("apple", "xiaomi", "oneplus", "oppo", "google", "motorola"), "phone"),
    (("intel", "dell", "lenovo", "micro-star", "gigabyte", "asustek", "microsoft"), "computer"),
]


def guess_type(host: Host, is_gateway: bool = False) -> str:
    """Best-effort, explainable guess. Order: ports (strongest evidence), then vendor."""
    if is_gateway:
        return "router"
    services = {p.service for p in host.open_ports}
    ports = {p.portid for p in host.open_ports}
    if "rtsp" in services or 554 in ports:
        return "camera"
    if "jetdirect" in services or "ipp" in services or 9100 in ports or 631 in ports:
        return "printer"
    if "ms-wbt-server" in services or "microsoft-ds" in services or "netbios-ssn" in services:
        return "computer"
    if "mqtt" in services:
        return "iot"
    if services & {"mysql", "postgresql", "redis", "mongodb"}:
        return "server"
    if {8008, 8009} & ports:
        return "tv"
    if "upnp" in services and ({80, 443} & ports):
        return "router"
    vendor = (host.vendor or "").lower()
    for keys, kind in _VENDOR_HINTS:
        if any(k in vendor for k in keys):
            return kind
    if host.ip.endswith(".1") and ({80, 443, 53} & ports):
        return "router"
    if "ssh" in services:
        return "server"
    return "unknown"


DEVICE_LABELS = {
    "router": {"ro": "Router", "en": "Router"},
    "camera": {"ro": "Cameră video", "en": "Camera"},
    "printer": {"ro": "Imprimantă", "en": "Printer"},
    "nas": {"ro": "Stocare în rețea (NAS)", "en": "Network storage (NAS)"},
    "iot": {"ro": "Dispozitiv inteligent", "en": "Smart device"},
    "tv": {"ro": "Televizor", "en": "TV"},
    "phone": {"ro": "Telefon / tabletă", "en": "Phone / tablet"},
    "computer": {"ro": "Calculator", "en": "Computer"},
    "server": {"ro": "Server", "en": "Server"},
    "unknown": {"ro": "Dispozitiv necunoscut", "en": "Unknown device"},
}
