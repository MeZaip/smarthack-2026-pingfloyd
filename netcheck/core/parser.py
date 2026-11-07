"""Safe nmap XML parser (NFR-03: hostile input).

* refuses DTDs / entity declarations (no XXE, no billion-laughs)
* enforces a size limit
* never raises anything except ScanFileError for a bad file
* everything read from the file (banners, titles, hostnames) is kept as plain text;
  escaping happens in the UI / exporters.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as _stdlib_et
from pathlib import Path

from .models import Host, Port, ScanResult

try:  # defusedxml is preferred when installed
    from defusedxml import ElementTree as _safe_et  # type: ignore
    from defusedxml.common import DefusedXmlException  # type: ignore
except ImportError:  # pragma: no cover - fallback path is guarded below
    _safe_et = None

    class DefusedXmlException(Exception):  # type: ignore
        pass


MAX_FILE_BYTES = int(os.environ.get("NETCHECK_MAX_FILE_MB", "50")) * 1024 * 1024
MAX_TEXT = 500  # truncate any single banner/script output we keep
_DOCTYPE_ANY = re.compile(rb"<!doctype[^>]*>?")
_DOCTYPE_NMAP = re.compile(rb"<!doctype\s+nmaprun\s*>")


class ScanFileError(Exception):
    """The file cannot be used. The message is safe to show to the user."""


def _clip(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\x00", "")
    return value[:MAX_TEXT]


def parse_file(path: str | os.PathLike) -> ScanResult:
    p = Path(path)
    try:
        size = p.stat().st_size
    except OSError as e:
        raise ScanFileError(f"cannot open file: {e.strerror}") from None
    if size == 0:
        raise ScanFileError("file is empty")
    if size > MAX_FILE_BYTES:
        raise ScanFileError(f"file too large ({size} bytes, limit {MAX_FILE_BYTES})")
    data = p.read_bytes()
    return parse_bytes(data, source=p.name)


def parse_bytes(data: bytes, source: str = "<memory>") -> ScanResult:
    if len(data) > MAX_FILE_BYTES:
        raise ScanFileError("file too large")
    # Real nmap output always starts with the bare line `<!DOCTYPE nmaprun>` (no internal
    # subset, no entities) - that exact form is allowed. Any other DOCTYPE, an internal
    # subset `[...]`, or any entity declaration is rejected outright (XXE / billion laughs);
    # this also covers the case where defusedxml is not installed.
    low = data.lower()
    if b"<!entity" in low:
        raise ScanFileError("file contains an entity declaration (refused for safety)")
    doctypes = _DOCTYPE_ANY.findall(low)
    if len(doctypes) > 1 or (doctypes and not _DOCTYPE_NMAP.fullmatch(doctypes[0])):
        raise ScanFileError("file contains a DTD declaration other than <!DOCTYPE nmaprun> (refused for safety)")
    try:
        if _safe_et is not None:
            root = _safe_et.fromstring(data, forbid_dtd=False, forbid_entities=True, forbid_external=True)
        else:
            root = _stdlib_et.fromstring(data)
    except (_stdlib_et.ParseError, DefusedXmlException, ValueError) as e:
        raise ScanFileError(f"not a valid XML file ({e.__class__.__name__}: {e})") from None
    if root.tag != "nmaprun":
        raise ScanFileError("not an nmap XML file (root element is not <nmaprun>)")

    hosts = [_parse_host(h) for h in root.findall("host")]
    start = root.get("start")
    return ScanResult(
        source=source,
        hosts=[h for h in hosts if h is not None],
        start_time=int(start) if start and start.isdigit() else None,
        args=_clip(root.get("args")),
    )


def _parse_host(el) -> Host | None:
    status_el = el.find("status")
    status = status_el.get("state", "unknown") if status_el is not None else "unknown"

    ip = mac = vendor = None
    for a in el.findall("address"):
        kind = a.get("addrtype")
        if kind in ("ipv4", "ipv6") and ip is None:
            ip = a.get("addr")
        elif kind == "mac":
            mac = a.get("addr")
            vendor = (a.get("vendor") or "").strip() or None
    if not ip:
        return None

    hostnames = []
    hn = el.find("hostnames")
    if hn is not None:
        for h in hn.findall("hostname"):
            name = (h.get("name") or "").strip()
            if name and name not in hostnames:
                hostnames.append(_clip(name))

    os_guess = None
    osm = el.find("os/osmatch")
    if osm is not None:
        os_guess = _clip(osm.get("name"))

    ports: list[Port] = []
    ports_el = el.find("ports")
    if ports_el is not None:
        for pe in ports_el.findall("port"):
            port = _parse_port(pe)
            if port is not None:
                ports.append(port)

    return Host(ip=ip, status=status, mac=mac, vendor=vendor,
                hostnames=hostnames, os_guess=os_guess, ports=ports)


def _parse_port(pe) -> Port | None:
    try:
        portid = int(pe.get("portid", ""))
    except ValueError:
        return None
    if not 0 <= portid <= 65535:
        return None
    st = pe.find("state")
    state = (st.get("state") if st is not None else "unknown") or "unknown"
    svc = pe.find("service")
    name = product = version = extrainfo = tunnel = ""
    if svc is not None:
        name = (svc.get("name") or "").strip().lower()
        product = _clip(svc.get("product"))
        version = _clip(svc.get("version"))
        extrainfo = _clip(svc.get("extrainfo"))
        tunnel = (svc.get("tunnel") or "").strip().lower()
    # nmap occasionally encodes TLS in the name itself ("ssl/http", "https")
    if name.startswith("ssl/"):
        name, tunnel = name[4:], "ssl"
    scripts = {}
    for sc in pe.findall("script"):
        sid = sc.get("id")
        if not sid:
            continue
        out = sc.get("output") or ""
        if sid == "http-title":
            title_elem = sc.find("elem[@key='title']")
            if title_elem is not None and title_elem.text:
                out = title_elem.text
        scripts[sid] = _clip(out.strip())
    return Port(protocol=(pe.get("protocol") or "").lower(), portid=portid, state=state.lower(),
                service=name, product=product, version=version, extrainfo=extrainfo,
                tunnel=tunnel, scripts=scripts)
