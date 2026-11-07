"""Contract between the netcheck app and the AI gateway (shared by both sides).

Privacy by design (NFR-02, ISO 27701): the app sends only what the model needs
to answer - device type, vendor, private IP, open ports and the findings with
their built-in texts. Hostnames, MAC addresses, raw XML and history never leave
the user's machine. The gateway re-builds the context from a whitelist, so any
extra field a client sends is dropped.

Request  (POST /v1/ask):  {"v": 1, "lang": "ro"|"en", "question": str, "context": {...},
                           "history": [{"role": "user"|"assistant", "content": str}, ...]}   (optional)
The gateway is stateless: the conversation lives in the app and is sent with each question.
Response (200):           {"answer": str, "model": str}
Errors:                   {"error": "<code>", "message": str} with 4xx/5xx
"""
from __future__ import annotations

import ipaddress
from typing import Any, Optional

from ..core.analysis import Analysis
from ..core.diff import compare
from ..core.rules import CATALOG, SEVERITY_RANK
from ..explain.texts import score_band, text_for

VERSION = 1
LANGS = ("ro", "en")
MAX_QUESTION = 1000
MAX_DEVICES = 64
MAX_PORTS_PER_DEVICE = 64
MAX_FINDINGS = 200
MAX_STR = 200
MAX_TITLE = 80
MAX_HISTORY_MESSAGES = 12      # last 6 question/answer pairs
MAX_HISTORY_CHARS = 2000
DEVICE_TYPES = ("router", "camera", "printer", "nas", "iot", "tv", "phone",
                "computer", "server", "unknown")


class ContractError(ValueError):
    """Request does not match the contract. Message is safe to return to the client."""


# ------------------------------------------------------------------ client side
def build_context(analysis: Analysis, lang: str = "ro", previous: Optional[Analysis] = None) -> dict:
    """Minimal, privacy-preserving view of one analysis (no hostnames, no MACs)."""
    if not analysis.ok:
        raise ValueError("cannot build context for an unreadable scan")
    devices = []
    for d in analysis.devices()[:MAX_DEVICES]:
        devices.append({
            "ip": d["ip"],
            "type": d["type"],
            "vendor": d["vendor"],
            "risk_points": d["risk_points"],
            "open_ports": [
                {"port": p["port"], "proto": p["protocol"], "service": p["service"],
                 "software": " ".join(x for x in (p["product"], p["version"]) if x) or None,
                 "tls": p["tls"], "title": (p["title"] or None) and p["title"][:MAX_TITLE]}
                for p in d["open_ports"][:MAX_PORTS_PER_DEVICE]
            ],
        })
    findings = []
    for f in analysis.prioritized()[:MAX_FINDINGS]:
        t = text_for(f.code, lang)
        findings.append({"ip": f.ip, "port": f.port, "code": f.code, "severity": f.severity,
                         "title": t["title"], "explanation": t["explain"], "steps": t["steps"]})
    changes = None
    if previous is not None and previous.ok:
        c = compare(previous, analysis)
        changes = {k: c[k] for k in ("score_before", "score_after", "new_devices", "removed_devices",
                                     "opened_ports", "closed_ports", "resolved_findings", "new_findings")}
    return {
        "score": analysis.score,
        "band": score_band(analysis.score, lang)["label"],
        "device_count": len(analysis.scan.up_hosts),
        "finding_count": len(analysis.findings),
        "devices": devices,
        "findings": findings,
        "changes": changes,
    }


def build_request(question: str, analysis: Analysis, lang: str = "ro",
                  previous: Optional[Analysis] = None, history: Optional[list[dict]] = None,
                  style: str = "text") -> dict:
    req = {"v": VERSION, "lang": lang if lang in LANGS else "ro",
           "question": (question or "").strip()[:MAX_QUESTION],
           "context": build_context(analysis, lang, previous)}
    if style == "voice":                 # optional field: the answer will be read aloud (voice mode)
        req["style"] = "voice"
    if history:
        h = [{"role": m["role"], "content": m["content"][:MAX_HISTORY_CHARS]} for m in history]
        h = h[-MAX_HISTORY_MESSAGES:]
        if h and h[0]["role"] != "user":   # keep it starting with a user turn
            h = h[1:]
        req["history"] = h
    return req


# ------------------------------------------------------------------ gateway side
def _str(v: Any, field: str, max_len: int = MAX_STR, optional: bool = True) -> Optional[str]:
    if v is None and optional:
        return None
    if not isinstance(v, str):
        raise ContractError(f"{field} must be a string")
    v = v.replace("\x00", "").strip()
    return v[:max_len]


def _int(v: Any, field: str, lo: int, hi: int, optional: bool = False) -> Optional[int]:
    if v is None and optional:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise ContractError(f"{field} must be an integer in [{lo}, {hi}]")
    return v


def _ip(v: Any, field: str) -> str:
    if not isinstance(v, str):
        raise ContractError(f"{field} must be an IP address")
    try:
        a = ipaddress.ip_address(v)
    except ValueError:
        raise ContractError(f"{field} must be an IP address") from None
    if not (a.is_private or a.is_link_local):
        # the app only ever scans private networks; anything else is not ours to discuss
        raise ContractError(f"{field} must be a private address")
    return str(a)


def _list(v: Any, field: str, max_items: int) -> list:
    if v is None:
        return []
    if not isinstance(v, list):
        raise ContractError(f"{field} must be a list")
    if len(v) > max_items:
        raise ContractError(f"{field} has too many items")
    return v


def _code(v: Any, field: str) -> str:
    if v not in CATALOG:
        raise ContractError(f"{field} is not a catalog code")
    return v


def _port_entry(p: Any, field: str) -> dict:
    if not isinstance(p, dict):
        raise ContractError(f"{field} must be an object")
    return {"ip": _ip(p.get("ip"), f"{field}.ip"), "protocol": _str(p.get("protocol"), f"{field}.protocol", 3),
            "port": _int(p.get("port"), f"{field}.port", 0, 65535), "service": _str(p.get("service"), f"{field}.service", 40)}


def _history(v: Any) -> list[dict]:
    items = _list(v, "history", MAX_HISTORY_MESSAGES)
    out = []
    for i, m in enumerate(items):
        if not isinstance(m, dict):
            raise ContractError(f"history[{i}] must be an object")
        expected = "user" if i % 2 == 0 else "assistant"
        if m.get("role") != expected:
            raise ContractError("history must alternate user/assistant, starting with user")
        content = _str(m.get("content"), f"history[{i}].content", MAX_HISTORY_CHARS, optional=False)
        if not content:
            raise ContractError(f"history[{i}].content is empty")
        out.append({"role": expected, "content": content})
    if len(out) % 2:
        raise ContractError("history must end with an assistant answer")
    return out


def request_style(obj: Any) -> str:
    """Optional "style" of a request: "voice" (answer read aloud: short, no addresses) or "text" (default)."""
    return "voice" if isinstance(obj, dict) and obj.get("style") == "voice" else "text"


def validate_request(obj: Any) -> tuple[str, str, dict, list[dict]]:
    """Return (lang, question, sanitized_context, history). Unknown fields are dropped."""
    if not isinstance(obj, dict):
        raise ContractError("body must be a JSON object")
    if obj.get("v") != VERSION:
        raise ContractError(f"unsupported contract version (expected {VERSION})")
    lang = obj.get("lang")
    if lang not in LANGS:
        raise ContractError("lang must be 'ro' or 'en'")
    question = _str(obj.get("question"), "question", MAX_QUESTION, optional=False)
    if not question:
        raise ContractError("question is empty")
    ctx = obj.get("context")
    if not isinstance(ctx, dict):
        raise ContractError("context must be an object")

    devices = []
    for i, d in enumerate(_list(ctx.get("devices"), "devices", MAX_DEVICES)):
        f = f"devices[{i}]"
        if not isinstance(d, dict):
            raise ContractError(f"{f} must be an object")
        dtype = d.get("type")
        if dtype not in DEVICE_TYPES:
            raise ContractError(f"{f}.type is invalid")
        ports = []
        for j, p in enumerate(_list(d.get("open_ports"), f"{f}.open_ports", MAX_PORTS_PER_DEVICE)):
            g = f"{f}.open_ports[{j}]"
            if not isinstance(p, dict):
                raise ContractError(f"{g} must be an object")
            proto = p.get("proto")
            if proto not in ("tcp", "udp"):
                raise ContractError(f"{g}.proto is invalid")
            ports.append({"port": _int(p.get("port"), f"{g}.port", 0, 65535), "proto": proto,
                          "service": _str(p.get("service"), f"{g}.service", 40),
                          "software": _str(p.get("software"), f"{g}.software", 80),
                          "tls": bool(p.get("tls")),
                          "title": _str(p.get("title"), f"{g}.title", MAX_TITLE)})
        devices.append({"ip": _ip(d.get("ip"), f"{f}.ip"), "type": dtype,
                        "vendor": _str(d.get("vendor"), f"{f}.vendor", 60),
                        "risk_points": _int(d.get("risk_points"), f"{f}.risk_points", 0, 10000),
                        "open_ports": ports})

    findings = []
    for i, x in enumerate(_list(ctx.get("findings"), "findings", MAX_FINDINGS)):
        f = f"findings[{i}]"
        if not isinstance(x, dict):
            raise ContractError(f"{f} must be an object")
        code = _code(x.get("code"), f"{f}.code")
        steps = [_str(s, f"{f}.steps", 300, optional=False) for s in _list(x.get("steps"), f"{f}.steps", 5)]
        findings.append({"ip": _ip(x.get("ip"), f"{f}.ip"),
                         "port": _int(x.get("port"), f"{f}.port", 0, 65535, optional=True),
                         "code": code,
                         # severity always comes from the catalog, never from the client
                         "severity": CATALOG[code].severity,
                         "title": _str(x.get("title"), f"{f}.title", 120),
                         "explanation": _str(x.get("explanation"), f"{f}.explanation", 400),
                         "steps": steps})
    findings.sort(key=lambda x: -SEVERITY_RANK[x["severity"]])

    changes = None
    c = ctx.get("changes")
    if c is not None:
        if not isinstance(c, dict):
            raise ContractError("changes must be an object")
        changes = {
            "score_before": _int(c.get("score_before"), "changes.score_before", 0, 100),
            "score_after": _int(c.get("score_after"), "changes.score_after", 0, 100),
            "new_devices": [_ip(v, "changes.new_devices") for v in _list(c.get("new_devices"), "changes.new_devices", MAX_DEVICES)],
            "removed_devices": [_ip(v, "changes.removed_devices") for v in _list(c.get("removed_devices"), "changes.removed_devices", MAX_DEVICES)],
            "opened_ports": [_port_entry(p, "changes.opened_ports") for p in _list(c.get("opened_ports"), "changes.opened_ports", 512)],
            "closed_ports": [_port_entry(p, "changes.closed_ports") for p in _list(c.get("closed_ports"), "changes.closed_ports", 512)],
            "resolved_findings": [{"ip": _ip(r.get("ip"), "changes.resolved_findings.ip"),
                                   "port": _int(r.get("port"), "changes.resolved_findings.port", 0, 65535, optional=True),
                                   "code": _code(r.get("code"), "changes.resolved_findings.code")}
                                  for r in _list(c.get("resolved_findings"), "changes.resolved_findings", MAX_FINDINGS)
                                  if isinstance(r, dict)],
            "new_findings": [{"ip": _ip(r.get("ip"), "changes.new_findings.ip"),
                              "port": _int(r.get("port"), "changes.new_findings.port", 0, 65535, optional=True),
                              "code": _code(r.get("code"), "changes.new_findings.code")}
                             for r in _list(c.get("new_findings"), "changes.new_findings", MAX_FINDINGS)
                             if isinstance(r, dict)],
        }

    sanitized = {
        "score": _int(ctx.get("score"), "score", 0, 100),
        "band": _str(ctx.get("band"), "band", 40),
        "device_count": _int(ctx.get("device_count"), "device_count", 0, 100000),
        "finding_count": _int(ctx.get("finding_count"), "finding_count", 0, 100000),
        "devices": devices,
        "findings": findings,
        "changes": changes,
    }
    return lang, question, sanitized, _history(obj.get("history"))


def evidence_from_context(ctx: dict) -> tuple[set[str], set[int], str]:
    """IPs, ports and free text the model is allowed to mention."""
    ips: set[str] = set()
    ports: set[int] = set()
    text: list[str] = []
    for d in ctx.get("devices") or []:
        ips.add(d["ip"])
        for p in d.get("open_ports") or []:
            ports.add(p["port"])
            text.extend(x for x in (p.get("software"), p.get("title")) if x)
    for f in ctx.get("findings") or []:
        ips.add(f["ip"])
        if f.get("port") is not None:
            ports.add(f["port"])
    c = ctx.get("changes") or {}
    ips.update(c.get("new_devices") or [])
    ips.update(c.get("removed_devices") or [])
    for key in ("opened_ports", "closed_ports", "resolved_findings", "new_findings"):
        for e in c.get(key) or []:
            ips.add(e["ip"])
            if e.get("port") is not None:
                ports.add(e["port"])
    return ips, ports, "\n".join(text)
