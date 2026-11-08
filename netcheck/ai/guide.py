"""„Pași pentru aparatul tău”: fix steps for one device brand/model, looked up by the assistant on the
maker's own support site. Shared by the app (builds the request) and the gateway (validates it).

Privacy (same rules as contract.py): only the maker, a model hint taken from what the device itself
announces (web page title / product name), the device type and the problem code leave the computer.
Never the IP, MAC, hostname or anything else from the network.

Request  (POST /v1/guide): {"v": 1, "lang": "ro"|"en", "vendor": "<key from VENDORS>", "model": str,
                            "type": "<device type>", "code": "<finding code>", "steps": [str, ...]}
Response (200):            {"answer": str, "sources": [{"title": str, "url": str}], "model": str}
"""
from __future__ import annotations

import re
from typing import Optional

from ..core.rules import CATALOG
from .contract import DEVICE_TYPES, LANGS, ContractError

VERSION = 1
MAX_MODEL = 80
MAX_STEP = 300
MAX_STEPS = 6

# maker -> (name shown to the user, words that identify it in the nmap vendor / product text,
#           official sites the search may use). Only these sites are searched: no forums, no blogs.
VENDORS: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "tplink": ("TP-Link", ("tp-link", "tplink", "tp link"), ("tp-link.com",)),
    "netgear": ("Netgear", ("netgear",), ("netgear.com",)),
    "asus": ("ASUS", ("asus", "asustek"), ("asus.com",)),
    "dlink": ("D-Link", ("d-link", "dlink"), ("dlink.com",)),
    "linksys": ("Linksys", ("linksys",), ("linksys.com",)),
    "huawei": ("Huawei", ("huawei",), ("consumer.huawei.com", "support.huawei.com")),
    "zte": ("ZTE", ("zte",), ("zte.com.cn", "ztedevices.com")),
    "xiaomi": ("Xiaomi", ("xiaomi",), ("mi.com",)),
    "mikrotik": ("MikroTik", ("mikrotik", "routerboard"), ("help.mikrotik.com", "mikrotik.com")),
    "ubiquiti": ("Ubiquiti", ("ubiquiti",), ("help.ui.com", "ui.com")),
    "avm": ("AVM FRITZ!Box", ("avm", "fritz"), ("avm.de", "en.avm.de")),
    "zyxel": ("Zyxel", ("zyxel",), ("zyxel.com",)),
    "tenda": ("Tenda", ("tenda",), ("tendacn.com",)),
    "cisco": ("Cisco", ("cisco",), ("cisco.com",)),
    "synology": ("Synology", ("synology",), ("kb.synology.com", "synology.com")),
    "qnap": ("QNAP", ("qnap",), ("qnap.com",)),
    "hikvision": ("Hikvision", ("hikvision",), ("hikvision.com",)),
    "dahua": ("Dahua", ("dahua",), ("dahuasecurity.com",)),
    "hp": ("HP", ("hewlett", "hp inc", "hewlett-packard"), ("support.hp.com", "hp.com")),
    "brother": ("Brother", ("brother",), ("support.brother.com",)),
    "epson": ("Epson", ("epson", "seiko epson"), ("epson.com", "epson.eu")),
    "canon": ("Canon", ("canon",), ("canon-europe.com", "canon.com")),
    "samsung": ("Samsung", ("samsung",), ("samsung.com",)),
    "lg": ("LG", ("lg electronics", "lg innotek"), ("lg.com",)),
    "apple": ("Apple", ("apple",), ("support.apple.com",)),
    "raspberrypi": ("Raspberry Pi", ("raspberry",), ("raspberrypi.com",)),
}

_WORD = re.compile(r"[a-z0-9]+(?:[-! ][a-z0-9]+)*")


def match_vendor(*texts: Optional[str]) -> Optional[str]:
    """Key in VENDORS for the first text that names a known maker (nmap vendor first, then products)."""
    for text in texts:
        low = " " + re.sub(r"[^a-z0-9!-]+", " ", (text or "").lower()) + " "
        for key, (_, words, _) in VENDORS.items():
            if any(f" {w} " in low or (len(w) > 4 and w in low) for w in words):
                return key
    return None


def _clean(text, limit: int) -> str:
    text = "".join(ch if ch.isprintable() else " " for ch in str(text or ""))
    return " ".join(text.split())[:limit]


def model_hint(device: dict) -> str:
    """What the device says about itself (web page title, product name): often the exact model."""
    parts = []
    for p in device.get("open_ports") or []:
        for v in (p.get("title"), p.get("product")):
            v = _clean(v, MAX_MODEL)
            if v and v not in parts and not re.fullmatch(r"(?i)(index|login|home|web ?ui|untitled)", v):
                parts.append(v)
    return _clean(" · ".join(parts), MAX_MODEL)


# Any other maker is searched too ("other:<Name>"): without a list of official sites, the search may use any site
# and every source is shown. Some makers only make the Wi-Fi chip inside other brands' devices (an "Espressif"
# smart plug is a Sonoff, Shelly, Tuya...): the answer says so and gives the steps of the usual setup apps.
CHIP_MAKERS = ("espressif", "realtek", "mediatek", "azurewave", "murata", "liteon", "lite-on", "hon hai", "foxconn",
               "quectel", "silicon labs", "texas instruments", "nordic", "beken", "bouffalo", "universal global")
_SUFFIX = re.compile(r"\b(inc|incorporated|co|corp|corporation|ltd|limited|llc|gmbh|ag|sa|srl|bv|oy|ab|plc|pte|"
                     r"technology|technologies|tech|systems|electronics|electronic|international|company)\b\.?", re.I)
_OTHER = re.compile(r"other:[A-Za-z0-9][A-Za-z0-9 .&+!-]{1,39}")


def maker_name(vendor_text: Optional[str]) -> Optional[str]:
    """'Espressif Inc.' -> 'Espressif'; 'Shenzhen Bilian Electronic Co.,Ltd' -> 'Shenzhen Bilian'."""
    text = re.sub(r"[^A-Za-z0-9 .&+!-]+", " ", vendor_text or "")
    text = _SUFFIX.sub(" ", text)
    words = [w.strip(".-") for w in text.split() if w.strip(".-")]
    name = " ".join(words[:3])[:40]
    return name if len(name) >= 2 and name.lower() not in ("unknown", "private") else None


def is_chip_maker(vendor: str) -> bool:
    low = vendor_name(vendor).lower()
    return any(w in low for w in CHIP_MAKERS)


def vendor_for(device: dict) -> Optional[str]:
    """A key of VENDORS, "other:<Name>" for any other maker we can name, or None (e.g. a private MAC)."""
    products = [p.get("product") for p in device.get("open_ports") or []]
    titles = [p.get("title") for p in device.get("open_ports") or []]
    known = match_vendor(device.get("vendor"), *products, *titles)
    if known:
        return known
    name = maker_name(device.get("vendor"))
    return f"other:{name}" if name else None


def build_guide_request(device: dict, code: str, steps: list[str], lang: str = "ro") -> dict:
    vendor = vendor_for(device)
    if not vendor:
        raise ValueError("unknown maker")
    return {"v": VERSION, "lang": lang if lang in LANGS else "ro", "vendor": vendor, "model": model_hint(device),
            "type": device.get("type") if device.get("type") in DEVICE_TYPES else "unknown",
            "code": code, "steps": [_clean(s, MAX_STEP) for s in steps[:MAX_STEPS]]}


def validate_guide_request(body) -> dict:
    """Gateway side: rebuild the request from a whitelist (extra fields are dropped)."""
    if not isinstance(body, dict) or body.get("v") != VERSION:
        raise ContractError("unsupported request version")
    lang = body.get("lang")
    if lang not in LANGS:
        raise ContractError("lang must be ro or en")
    vendor = body.get("vendor")
    if vendor not in VENDORS and not (isinstance(vendor, str) and _OTHER.fullmatch(vendor)):
        raise ContractError("unknown vendor")
    code = body.get("code")
    if code not in CATALOG:
        raise ContractError("unknown finding code")
    typ = body.get("type") if body.get("type") in DEVICE_TYPES else "unknown"
    steps = body.get("steps") or []
    if not isinstance(steps, list) or not all(isinstance(s, str) for s in steps):
        raise ContractError("steps must be a list of strings")
    return {"lang": lang, "vendor": vendor, "model": _clean(body.get("model"), MAX_MODEL), "type": typ,
            "code": code, "steps": [_clean(s, MAX_STEP) for s in steps[:MAX_STEPS] if s.strip()]}


def domains(vendor: str) -> list[str]:
    """Official sites the search is limited to; [] = no list known, any site (sources are always shown)."""
    return list(VENDORS[vendor][2]) if vendor in VENDORS else []


def vendor_name(vendor: str) -> str:
    return VENDORS[vendor][0] if vendor in VENDORS else vendor.split(":", 1)[-1]


# ---------------------------------------------------------------- the chat: "how do I do it on my TP-Link?"
_ASKS_STEPS = re.compile(
    r"pa[sș]i|cum\b|unde\b|meniu|set[aă]ri|instruc[tț]iun|exact|specific|model|dezactivez|opresc|repar|apas|apăs"
    r"|steps?\b|\bhow\b|\bwhere\b|menu|setting|instruction|disable|turn off|\bfix\b|click", re.I)
_ROUTER_WORDS = re.compile(r"\brouter", re.I)
_TYPE_WORDS = [("iot", r"priz|\bbec|senzor|smart|plug|bulb|sensor|întrerup|switch"), ("camera", r"camer"),
               ("printer", r"imprimant|printer"), ("tv", r"televizor|\btv\b"), ("nas", r"\bnas\b|stocare|storage")]
# a problem named in the question -> its code (otherwise the device's most dangerous problem is used)
_CODE_WORDS = [
    ("TELNET_OPEN", r"telnet"), ("UPNP_EXPOSED", r"upnp"), ("SNMP_EXPOSED", r"snmp"), ("FTP_CLEARTEXT", r"\bftp"),
    ("SMB_EXPOSED", r"\bsmb|partaj|file shar"), ("RDP_EXPOSED", r"\brdp|remote desktop|desktop la distan"),
    ("VNC_EXPOSED", r"\bvnc"), ("MQTT_EXPOSED", r"mqtt"), ("CAMERA_STREAM_EXPOSED", r"rtsp|camer"),
    ("HTTP_ADMIN_CLEARTEXT", r"https?\b|pagina de set|settings page|admin"), ("DB_EXPOSED", r"baz[aă] de date|database"),
    ("PRINTER_RAW_EXPOSED", r"imprimant|printer|9100"), ("OUTDATED_SERVICE", r"actualiz|update|firmware|vech|outdated"),
]


def device_steps_target(question: str, devices: list[dict], findings: list, earlier: str = "") -> Optional[tuple[dict, str]]:
    """(device, finding code) when the question asks how to fix something on a device whose maker we know,
    e.g. "cum opresc telnet pe TP-Link?" or "pașii pentru routerul meu". None for any other question."""
    text = f"{earlier} {question}"
    if not _ASKS_STEPS.search(question):
        return None
    known = [d for d in devices if vendor_for(d)]
    maker = match_vendor(question) or match_vendor(earlier)
    device = next((d for d in known if maker and vendor_for(d) == maker), None)
    if device is None:                       # "cum fac pe Espressif?": any maker's name in the question
        low = f" {re.sub(r'[^a-z0-9]+', ' ', text.lower())} "
        device = next((d for d in known if vendor_for(d).startswith("other:")
                       and f" {vendor_name(vendor_for(d)).split()[0].lower()} " in low), None)
    if device is None and _ROUTER_WORDS.search(text):
        device = next((d for d in known if d.get("type") == "router"), None)
    if device is None:                       # "cum repar priza / camera / imprimanta?": the only device of that kind
        for typ, words in _TYPE_WORDS:
            if re.search(words, text, re.I):
                same = [d for d in known if d.get("type") == typ]
                if len(same) == 1:
                    device = same[0]
                    break
    if device is None:
        return None
    mine = [f for f in findings if f.ip == device["ip"] and f.severity != "info"]
    if not mine:
        return None
    for code, words in _CODE_WORDS:
        if re.search(words, question, re.I) and any(f.code == code for f in mine):
            return device, code
    return device, mine[0].code              # findings come most dangerous first
