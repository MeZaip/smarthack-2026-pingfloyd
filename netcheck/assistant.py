"""AI assistant used by `netcheck chat` (CLI) and the Q&A box in the web UI (FR-12).

Governance (NFR-06):
  * The model never computes findings or scores. It can only CALL our deterministic tools
    and read their JSON output. Everything it says must come from those results.
  * Live scans go through guardrail.check_target() AND an explicit yes from the human
    (confirm callback). The model cannot bypass either.
  * Every AI answer is checked by check_grounded(): any IP, port, finding code, CVE, link or phone number
    that is not in the scan evidence -> the answer is rejected and the verified built-in text is shown.
  * No model / network / refusal  ->  built-in offline answerer (keyword intents + texts.json).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Callable

from . import explain, guardrail, history, llm, netdetect
from .analyzer import analyze_file, most_dangerous, ranked_findings
from .models import ScanResult

SYSTEM_PROMPT = """You are NetCheck, a friendly home-network safety helper for people with no technical background \
(think: a parent or grandparent). You help them understand a scan of THEIR OWN network and fix problems one step at a time.

Hard rules:
- Every fact you state about the network (devices, ports, services, versions, findings, scores) MUST come from the \
SCAN CONTEXT below or from a tool result. Use the tools for details (fix steps, comparisons).
- Call devices by their personal name when they have one (field "name").
- If the tools do not contain the answer, say clearly: "The scan does not show this." (in Romanian: \
"Scanarea nu arată asta."). Never guess. Never invent ports, devices, CVE numbers, phone numbers, links or brand-specific \
menus that the tools did not give you.
- Never change, add or remove findings, severities or scores. They come from fixed rules; you only explain them.
- Live scans: only via the start_live_scan tool. It enforces the safety rules and asks the human to confirm. \
Never suggest scanning networks or devices the user does not own.
- Language: answer in {lang_name}. Use short sentences a 12-year-old understands. Explain any technical word you use.
- Be concise: at most ~6 short lines unless the user asks for more. When giving a fix, give numbered steps \
(the steps from get_fix are the reference) and suggest re-scanning afterwards to prove it worked.
"""

TOOLS = [
    {
        "name": "get_scan_summary",
        "description": "Summary of the currently loaded scan: file name, standard score (0-100), number of devices and "
                       "findings by severity, the most dangerous device and the first thing to fix. Call this first.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "list_devices",
        "description": "All devices in the loaded scan with IP, masked MAC, vendor, hostname, device-type guess, "
                       "open ports (port, protocol, service, product, version) and risk points.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "list_findings",
        "description": "Findings (security problems) in the loaded scan, most dangerous first, each with code, severity, "
                       "points, port, evidence and the built-in plain-language explanation. Optionally filter by device IP.",
        "input_schema": {
            "type": "object",
            "properties": {"ip": {"type": "string", "description": "Only findings for this IP (optional)"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_fix",
        "description": "Built-in explanation, step-by-step fix and references (CIS / OWASP IoT) for one finding code, "
                       "e.g. TELNET_OPEN, UPNP_EXPOSED.",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
            "additionalProperties": False,
        },
    },
    {
        "name": "compare_with_previous",
        "description": "Compare the loaded scan with the previous scan in history: new/removed devices, opened/closed "
                       "ports, resolved/new findings, score change.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "detect_network",
        "description": "Detect the network this computer is connected to (interface, own IP, subnet, gateway).",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "start_live_scan",
        "description": "Scan the user's own network. Target defaults to the connected subnet. The tool enforces the "
                       "allowlist, refuses public IPs and ASKS THE HUMAN to confirm. Returns the new scan summary or a refusal.",
        "input_schema": {
            "type": "object",
            "properties": {"target": {"type": "string", "description": "IP or CIDR; omit to use the connected subnet"}},
            "additionalProperties": False,
        },
    },
]


@dataclass
class Session:
    lang: str = "ro"
    result: ScanResult | None = None
    scan_id: int | None = None
    allow_live_scan: bool = False
    confirm: Callable[[str], bool] | None = None   # asks the human; returns True only on explicit yes
    extra_allow: list[str] = field(default_factory=list)
    history_source: str = "lab"

    def name_of(self, ip: str) -> str:
        """Personal nickname of the device at this IP in the loaded scan, or ''."""
        if self.result is None:
            return ""
        nick = history.nicknames()
        dev = next((d for d in self.result.devices if d.ip == ip), None)
        return nick.get(dev.device_id, "") if dev and dev.device_id else ""

    def load_file(self, path: str) -> ScanResult:
        self.result = analyze_file(path)
        self.scan_id = history.save(self.result, self.history_source) if self.result.ok else None
        return self.result

    def load_history(self, scan_id: int) -> ScanResult | None:
        r = history.load(scan_id)
        if r:
            self.result, self.scan_id = r, scan_id
        return r


# ----------------------------------------------------------------- deterministic tools
def _finding_view(f, lang, name=""):
    t = explain.get(f.code, lang)
    return {"ip": f.ip, "name": name, "port": f.port, "protocol": f.protocol, "code": f.code, "severity": f.severity,
            "points": f.points, "evidence": f.evidence, "title": t["title"], "explanation": t["explain"]}


def tool_summary(s: Session) -> dict:
    r = s.result
    if r is None:
        return {"error": "No scan loaded. Load a scan file or start a live scan first."}
    if not r.ok:
        return {"file": r.file, "error": f"This file could not be read: {r.error}", "score": "ERROR"}
    dev, first = most_dangerous(r)
    counts: dict[str, int] = {}
    for f in r.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    out = {"file": r.file, "standard_score": r.score, "devices": len(r.devices),
           "findings_by_severity": counts, "most_dangerous_device": None, "fix_first": None}
    if dev and first:
        out["most_dangerous_device"] = {"ip": dev.ip, "name": s.name_of(dev.ip), "type_guess": dev.type_guess,
                                        "vendor": dev.vendor, "hostname": dev.hostname,
                                        "risk_points": dev.risk_points}
        fx = explain.get(first.code, s.lang)
        out["fix_first"] = {**_finding_view(first, s.lang, s.name_of(first.ip)), "steps": fx["steps"]}
    return out


def tool_devices(s: Session) -> dict:
    if s.result is None or not s.result.ok:
        return tool_summary(s)
    devs = []
    for d in s.result.devices:
        x = d.to_dict()
        x.pop("device_id", None)
        x["name"] = s.name_of(d.ip)
        devs.append(x)
    return {"devices": devs}


def tool_findings(s: Session, ip: str | None = None) -> dict:
    if s.result is None or not s.result.ok:
        return tool_summary(s)
    fs = [f for f in ranked_findings(s.result) if not ip or f.ip == ip]
    return {"findings": [_finding_view(f, s.lang, s.name_of(f.ip)) for f in fs],
            "note": "No findings for this device." if ip and not fs else ""}


def tool_fix(s: Session, code: str) -> dict:
    code = (code or "").strip().upper()
    if code not in explain.all_codes():
        return {"error": f"Unknown finding code '{code}'. Known codes: {', '.join(explain.all_codes())}"}
    return {"code": code, **explain.get(code, s.lang)}


def tool_compare(s: Session) -> dict:
    if s.scan_id is None:
        return {"error": "The loaded scan is not in history, nothing to compare."}
    prev = history.previous_of(s.scan_id)
    if prev is None:
        return {"error": "There is no earlier scan to compare with. Fix something, scan again, then compare."}
    old = history.load(prev)
    d = history.diff(old, s.result)
    d["alerts"] = history.alerts(d, s.lang)
    return d


def tool_detect(s: Session) -> dict:
    try:
        return netdetect.detect().to_dict()
    except netdetect.NetworkDetectError as e:
        return {"error": str(e)}


def tool_live_scan(s: Session, target: str | None = None) -> dict:
    from . import scanner  # local import: only needed for live scans
    if not s.allow_live_scan:
        return {"error": "Live scanning is not available here. Use the command line: netcheck scan --confirm"}
    try:
        net = netdetect.detect()
        allow = guardrail.build_allowlist(net.subnet, s.extra_allow)
        target = (target or net.subnet).strip()
        guardrail.check_target(target, allow, confirmed=True)  # scope check first...
    except (netdetect.NetworkDetectError, guardrail.ScopeError) as e:
        return {"refused": str(e)}
    question = (f"Scanez rețeaua {target}? Confirmi că toate dispozitivele din ea sunt ale tale? (da/nu) "
                if s.lang == "ro" else
                f"Scan network {target}? Do you confirm you own every device on it? (yes/no) ")
    if not (s.confirm and s.confirm(question)):              # ...then the human's explicit consent
        return {"refused": "The user did not confirm the scan."}
    try:
        xml = scanner.run_scan(target)
    except scanner.ScanError as e:
        return {"error": str(e)}
    s.load_file(str(xml))
    return {"scan_file": str(xml), **tool_summary(s)}


def run_tool(s: Session, name: str, args: dict) -> dict:
    args = args if isinstance(args, dict) else {}
    if name == "get_scan_summary":
        return tool_summary(s)
    if name == "list_devices":
        return tool_devices(s)
    if name == "list_findings":
        ip = args.get("ip")
        return tool_findings(s, ip if isinstance(ip, str) else None)
    if name == "get_fix":
        return tool_fix(s, str(args.get("code", "")))
    if name == "compare_with_previous":
        return tool_compare(s)
    if name == "detect_network":
        return tool_detect(s)
    if name == "start_live_scan":
        t = args.get("target")
        return tool_live_scan(s, t if isinstance(t, str) else None)
    return {"error": f"unknown tool {name}"}


# ----------------------------------------------------------------- grounding (NFR-06)
_IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_PORT_RE = re.compile(r"(?:\bport(?:ul|urile|s|ului)?\s+|\b\d{1,3}(?:\.\d{1,3}){3}:)(\d{1,5})\b", re.I)
_CODE_RE = re.compile(r"\b[A-Z]{2,}(?:_[A-Z]+)+\b")
_FORBIDDEN = [(re.compile(r"CVE-\d{4}-\d+", re.I), "CVE number"),
              (re.compile(r"https?://\S+", re.I), "link"),
              (re.compile(r"(?:\+\d{1,3}[\s.-]?)?\b0?\d{3}[\s.-]?\d{3}[\s.-]?\d{3,4}\b"), "phone number")]


def scan_context(s: Session) -> dict:
    """Compact, verified facts given to the model up front (helps small local models)."""
    if s.result is None:
        return {"scan": None}
    if not s.result.ok:
        return {"file": s.result.file, "score": "ERROR", "error": s.result.error}
    return {
        "summary": tool_summary(s),
        "devices": [{"ip": d.ip, "name": s.name_of(d.ip), "type": d.type_guess, "vendor": d.vendor,
                     "hostname": d.hostname, "open_ports": [f"{p['port']}/{p['protocol']} {p['service']}"
                                                            for p in d.open_ports], "risk_points": d.risk_points}
                    for d in s.result.devices],
        "findings": [{"ip": f.ip, "name": s.name_of(f.ip), "port": f.port, "code": f.code, "severity": f.severity,
                      "points": f.points, "title": explain.get(f.code, s.lang)["title"]}
                     for f in ranked_findings(s.result)],
    }


def check_grounded(answer: str, s: Session, evidence: list[str], question: str = "") -> list[str]:
    """Return problems: things the AI said that are NOT backed by the scan (empty list = OK)."""
    ev = "\n".join(evidence + [json.dumps(scan_context(s), ensure_ascii=False), question])
    known_ports = {p["port"] for d in (s.result.devices if s.result and s.result.ok else []) for p in d.open_ports}
    known_ports |= {int(n) for n in re.findall(r'"port":\s*(\d+)', ev)}
    known_ports |= {int(n) for n in re.findall(r"\b(\d{1,5})\b", question)}
    problems = []
    for ip in set(_IP_RE.findall(answer)):
        if ip not in ev:
            problems.append(f"IP {ip}")
    for n in set(_PORT_RE.findall(answer)):
        if int(n) not in known_ports:
            problems.append(f"port {n}")
    for code in set(_CODE_RE.findall(answer)):
        if code in explain.all_codes() and code not in ev:
            problems.append(f"finding {code}")
    for rx, what in _FORBIDDEN:
        for m in rx.findall(answer):
            if m not in ev and not _IP_RE.fullmatch(m.strip()):
                problems.append(f"{what} {m}")
    return problems


# ----------------------------------------------------------------- LLM assistant
class Assistant:
    def __init__(self, session: Session, provider=None):
        self.s = session
        self.last_mode = "offline"
        self.last_problems: list[str] = []
        if provider is not None:
            self.provider, self.status = provider, getattr(provider, "label", "custom")
        else:
            self.provider, self.status = llm.select_provider()

    @property
    def online(self) -> bool:
        return self.provider is not None

    def _tools(self):
        return [t for t in TOOLS if self.s.allow_live_scan or t["name"] != "start_live_scan"]

    def _system(self) -> str:
        lang_name = "Romanian" if self.s.lang == "ro" else "English"
        return (SYSTEM_PROMPT.format(lang_name=lang_name)
                + "\n\nSCAN CONTEXT (verified facts from fixed rules, JSON):\n"
                + json.dumps(scan_context(self.s), ensure_ascii=False))

    def ask(self, question: str) -> str:
        question = question.strip()[:2000]
        if not question:
            return ""
        if self.provider is None:
            self.last_mode = "offline"
            return offline_answer(self.s, question)
        try:
            text, evidence = self.provider.run(self._system(), self._tools(), question,
                                               lambda n, a: run_tool(self.s, n, a))
        except Exception as e:  # model down, timeout, refusal... -> built-in text
            self.last_mode = "offline"
            note = ("(AI indisponibil, răspund din textele integrate)" if self.s.lang == "ro"
                    else "(AI unavailable, answering from built-in texts)")
            return f"{note} [{type(e).__name__}]\n" + offline_answer(self.s, question)
        self.last_problems = check_grounded(text, self.s, evidence, question) if text else ["empty answer"]
        if self.last_problems:
            self.last_mode = "rejected"
            note = (f"(AI-ul a menționat ceva ce nu e în scanare: {', '.join(self.last_problems)} — "
                    "îți arăt textul verificat)" if self.s.lang == "ro" else
                    f"(The AI mentioned something not in the scan: {', '.join(self.last_problems)} — "
                    "showing the verified text instead)")
            return note + "\n" + offline_answer(self.s, question)
        self.last_mode = "ai"
        return text


# ----------------------------------------------------------------- offline answerer
_CODE_WORDS = {
    "telnet": "TELNET_OPEN", "rdp": "RDP_EXPOSED", "remote desktop": "RDP_EXPOSED", "desktop la distan": "RDP_EXPOSED",
    "vnc": "VNC_EXPOSED", "screen shar": "VNC_EXPOSED", "partajare ecran": "VNC_EXPOSED",
    "database": "DB_EXPOSED", "baza de date": "DB_EXPOSED", "bază de date": "DB_EXPOSED", "redis": "DB_EXPOSED",
    "mysql": "DB_EXPOSED", "postgres": "DB_EXPOSED", "mongo": "DB_EXPOSED",
    "camera": "CAMERA_STREAM_EXPOSED", "cameră": "CAMERA_STREAM_EXPOSED", "rtsp": "CAMERA_STREAM_EXPOSED",
    "outdated": "OUTDATED_SERVICE", "vechi": "OUTDATED_SERVICE", "update": "OUTDATED_SERVICE", "actualiz": "OUTDATED_SERVICE",
    "ftp": "FTP_CLEARTEXT", "admin": "HTTP_ADMIN_CLEARTEXT", "http": "HTTP_ADMIN_CLEARTEXT",
    "smb": "SMB_EXPOSED", "file shar": "SMB_EXPOSED", "partajare fi": "SMB_EXPOSED",
    "mqtt": "MQTT_EXPOSED", "upnp": "UPNP_EXPOSED", "snmp": "SNMP_EXPOSED",
    "printer": "PRINTER_RAW_EXPOSED", "imprimant": "PRINTER_RAW_EXPOSED", "jetdirect": "PRINTER_RAW_EXPOSED",
    "unknown": "UNKNOWN_DEVICE", "necunoscut": "UNKNOWN_DEVICE", "ssh": "SSH_OPEN",
}


def _L(s: Session, ro: str, en: str) -> str:
    return ro if s.lang == "ro" else en


def _fmt_fix(s: Session, f) -> str:
    t = explain.get(f.code, s.lang)
    where = f"{f.ip}" + (f":{f.port}" if f.port is not None else "")
    nick = s.name_of(f.ip)
    if nick:
        where = f"„{nick}” ({where})"
    steps = "\n".join(f"  {i}. {x}" for i, x in enumerate(t["steps"], 1))
    return (f"{explain.SEVERITY_ICON[f.severity]} {t['title']} — {where} "
            f"[{explain.SEVERITY_LABEL[s.lang][f.severity]}]\n{t['explain']}\n"
            f"{_L(s, 'Ce faci:', 'What to do:')}\n{steps}\n"
            f"{_L(s, 'Dovada din scanare:', 'Evidence from the scan:')} {f.evidence}")


def offline_answer(s: Session, q: str) -> str:
    ql = q.lower()
    r = s.result
    help_text = _L(s,
                   "Pot răspunde doar din scanarea ta. Încearcă: „care e cel mai periculos dispozitiv?”, "
                   "„ce repar primul?”, „ce dispozitive am?”, „ce înseamnă portul 9100?”, „ce s-a schimbat?”, „scorul”.",
                   "I can only answer from your scan. Try: \"which device is most dangerous?\", \"what do I fix first?\", "
                   "\"what devices do I have?\", \"what does port 9100 mean?\", \"what changed?\", \"score\".")
    if any(w in ql for w in ("help", "ajutor", "ce poti", "ce poți", "what can")):
        return help_text
    if r is None:
        return _L(s, "Nu am încă o scanare. Încarcă un fișier (load <fișier.xml>) sau scrie „scan”.",
                  "No scan loaded yet. Load a file (load <file.xml>) or type \"scan\".")
    if not r.ok:
        return _L(s, f"Fișierul {r.file} nu poate fi citit: {r.error}. Scorul este ERROR.",
                  f"The file {r.file} cannot be read: {r.error}. The score is ERROR.")

    if any(w in ql for w in ("schimbat", "diferen", "before", "after", "înainte", "inainte", "changed", "istoric",
                             "history", "compar", "rezolvat", "resolved")):
        d = tool_compare(s)
        if "error" in d:
            return _L(s, "Nu am o scanare anterioară cu care să compar.", "There is no earlier scan to compare with.")
        lines = [_L(s, f"Scor: {d['old_score']} → {d['new_score']} ({d['score_delta']:+d})",
                    f"Score: {d['old_score']} → {d['new_score']} ({d['score_delta']:+d})")]
        for f in d["resolved_findings"]:
            lines.append(_L(s, "✔ Rezolvat: ", "✔ Resolved: ") + f"{explain.get(f['code'], s.lang)['title']} ({f['ip']})")
        for f in d["new_findings"]:
            lines.append(_L(s, "⚠ Nou: ", "⚠ New: ") + f"{explain.get(f['code'], s.lang)['title']} ({f['ip']})")
        lines += ["🔔 " + a for a in d["alerts"]]
        return "\n".join(lines)

    # a specific port number?
    m = re.search(r"\b(\d{1,5})\b", ql)
    if m and any(w in ql for w in ("port", "portul")):
        num = int(m.group(1))
        fs = [f for f in r.findings if f.port == num]
        if fs:
            return "\n\n".join(_fmt_fix(s, f) for f in fs)
        opens = [(d, p) for d in r.devices for p in d.open_ports if p["port"] == num]
        if opens:
            d, p = opens[0]
            return _L(s, f"Portul {num} este deschis pe {d.ip} (serviciu: {p['service'] or 'necunoscut'}). "
                         "Nu e în lista noastră oficială de riscuri, deci nu scade scorul.",
                      f"Port {num} is open on {d.ip} (service: {p['service'] or 'unknown'}). "
                      "It is not in our official risk list, so it does not lower the score.")
        return _L(s, f"Scanarea nu arată portul {num} deschis pe niciun dispozitiv.",
                  f"The scan does not show port {num} open on any device.")

    if any(w in ql for w in ("pericul", "danger", "worst", "risky", "cel mai rău", "prim", "first", "încep", "incep",
                             "start", "ce fac", "what do i do", "what should")):
        dev, first = most_dangerous(r)
        if not dev:
            return _L(s, f"Vești bune: nu am găsit probleme. Scor {r.score}/100.",
                      f"Good news: no problems found. Score {r.score}/100.")
        name = s.name_of(dev.ip) or dev.hostname or dev.vendor or dev.type_guess
        return (_L(s, f"Cel mai periculos dispozitiv: {dev.ip} ({name}, {dev.type_guess}), {dev.risk_points} puncte de risc.\n"
                      "Repară primul:\n",
                   f"Most dangerous device: {dev.ip} ({name}, {dev.type_guess}), {dev.risk_points} risk points.\n"
                   "Fix this first:\n") + _fmt_fix(s, first))

    if any(w in ql for w in ("scor", "score", "nota", "notă")):
        band = explain.score_band(r.score, s.lang)
        return _L(s, f"Scorul rețelei: {r.score}/100 {band[1]} {band[2]}. Pornim de la 100 și scădem puncte pentru "
                     "fiecare problemă (20 risc ridicat, 10 mediu, 5 scăzut).",
                  f"Network score: {r.score}/100 {band[1]} {band[2]}. We start at 100 and subtract points for each "
                  "problem (20 high, 10 medium, 5 low).")

    if any(w in ql for w in ("dispozitiv", "device", "conectat", "connected", "cine e", "who is", "list")):
        lines = [f"• {d.ip} — {(('„' + s.name_of(d.ip) + '” ') if s.name_of(d.ip) else '')}{d.hostname or '?'} / {d.vendor or '?'} ({d.type_guess}), "
                 + _L(s, f"{len(d.open_ports)} porturi deschise, {d.risk_points} puncte risc",
                      f"{len(d.open_ports)} open ports, {d.risk_points} risk points") for d in r.devices]
        return "\n".join(lines) or _L(s, "Scanarea nu arată dispozitive.", "The scan shows no devices.")

    for word, code in _CODE_WORDS.items():
        if word in ql or code.lower() in ql:
            fs = [f for f in r.findings if f.code == code]
            if fs:
                return "\n\n".join(_fmt_fix(s, f) for f in fs)
            t = explain.get(code, s.lang)
            return _L(s, f"Scanarea ta nu arată problema „{t['title']}”. Pe scurt: {t['explain']}",
                      f"Your scan does not show \"{t['title']}\". In short: {t['explain']}")
    m = re.search(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", ql)
    if m:
        fs = [f for f in ranked_findings(r) if f.ip == m.group(1)]
        if fs:
            return "\n\n".join(_fmt_fix(s, f) for f in fs)
        return _L(s, f"Scanarea nu arată probleme pentru {m.group(1)}.", f"The scan shows no problems for {m.group(1)}.")
    return _L(s, "Scanarea nu arată asta. ", "The scan does not show this. ") + help_text
