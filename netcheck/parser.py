"""Safe nmap XML parser (NFR-03).

- defusedxml blocks external entities / entity expansion (XXE, billion laughs).
- Files larger than MAX_FILE_BYTES are refused before parsing.
- All text from the scan (titles, banners) is kept as plain untrusted strings;
  the UI escapes it (Jinja2 autoescape).
"""
from __future__ import annotations

import os
from pathlib import Path

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError

from .models import Host, Port

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_TEXT = 500  # cap any single string we keep from the file


class ScanFileError(Exception):
    """Raised when a scan file cannot be read. Message is user-facing."""


def _txt(value: str | None) -> str:
    if not value:
        return ""
    return value.strip()[:MAX_TEXT]


def parse_file(path: str | os.PathLike) -> list[Host]:
    return parse_bytes(read_file(path))


def read_file(path: str | os.PathLike) -> bytes:
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError as e:
        raise ScanFileError(f"cannot open file: {e.strerror}") from None
    if size == 0:
        raise ScanFileError("file is empty")
    if size > MAX_FILE_BYTES:
        raise ScanFileError(f"file too large ({size} bytes, limit {MAX_FILE_BYTES})")
    try:
        return path.read_bytes()
    except OSError as e:
        raise ScanFileError(f"cannot read file: {e.strerror}") from None


def parse_bytes(data: bytes) -> list[Host]:
    if len(data) > MAX_FILE_BYTES:
        raise ScanFileError("file too large")
    try:
        root = SafeET.fromstring(data, forbid_dtd=False, forbid_entities=True, forbid_external=True)
    except DefusedXmlException:
        raise ScanFileError("file contains forbidden XML entities (rejected for safety)") from None
    except ParseError as e:
        raise ScanFileError(f"not valid XML (truncated or corrupted): {e}") from None
    if root.tag != "nmaprun":
        raise ScanFileError(f"not an nmap XML file (root element is <{root.tag}>)")

    hosts: list[Host] = []
    for h in root.findall("host"):
        status = h.find("status")
        if status is not None and status.get("state") == "down":
            continue
        ip = mac = vendor = ""
        for addr in h.findall("address"):
            t = addr.get("addrtype")
            if t in ("ipv4", "ipv6") and not ip:
                ip = _txt(addr.get("addr"))
            elif t == "mac":
                mac = _txt(addr.get("addr"))
                vendor = _txt(addr.get("vendor"))
        if not ip:
            continue
        hostname = ""
        hn = h.find("hostnames")
        if hn is not None:
            for name in hn.findall("hostname"):
                if name.get("name"):
                    hostname = _txt(name.get("name"))
                    break
        host = Host(ip=ip, mac=mac, vendor=vendor, hostname=hostname)
        ports_el = h.find("ports")
        if ports_el is not None:
            for p in ports_el.findall("port"):
                host.ports.append(_parse_port(p))
        hosts.append(host)
    return hosts


def _parse_port(p) -> Port:
    try:
        portid = int(p.get("portid", "0"))
    except ValueError:
        portid = 0
    st = p.find("state")
    svc = p.find("service")
    port = Port(
        protocol=_txt(p.get("protocol")).lower(),
        portid=portid,
        state=_txt(st.get("state")) if st is not None else "",
    )
    if svc is not None:
        port.service = _txt(svc.get("name")).lower()
        port.product = _txt(svc.get("product"))
        port.version = _txt(svc.get("version"))
        port.extrainfo = _txt(svc.get("extrainfo"))
        port.tunnel = _txt(svc.get("tunnel")).lower()
    banners = []
    for s in p.findall("script"):
        sid = s.get("id", "")
        if sid == "http-title":
            title_elem = s.find("elem[@key='title']")
            port.title = _txt(title_elem.text if title_elem is not None and title_elem.text else s.get("output"))
        else:
            banners.append(f"{sid}: {_txt(s.get('output'))}")
    port.banner = _txt(" | ".join(banners))
    return port
