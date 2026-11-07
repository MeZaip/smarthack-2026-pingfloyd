"""Builds the 'house map': each device is a room, each open port is a door."""
from __future__ import annotations

from .. import explain
from ..analyzer import most_dangerous
from ..models import ScanResult
from ..rules import SEVERITY_ORDER, _ip_key

ICONS = {"router": "📡", "camera": "📷", "printer": "🖨️", "nas": "🗄️", "tv / media": "📺",
         "iot / smart home": "💡", "phone / tablet": "📱", "computer": "💻", "server": "🖥️", "unknown": "❓"}
TYPE_RO = {"router": "router", "camera": "cameră", "printer": "imprimantă", "nas": "stocare (NAS)",
           "tv / media": "TV / media", "iot / smart home": "smart home", "phone / tablet": "telefon / tabletă",
           "computer": "calculator", "server": "server", "unknown": "necunoscut"}


def display_name(dev, nick: dict, lang: str) -> str:
    return nick.get(dev.device_id) or dev.hostname or dev.vendor or (
        TYPE_RO.get(dev.type_guess, dev.type_guess) if lang == "ro" else dev.type_guess)


def rooms(r: ScanResult, nick: dict, verifications: dict, lang: str) -> list[dict]:
    if not r or not r.ok:
        return []
    worst_dev, _ = most_dangerous(r)
    by_port: dict[tuple, list] = {}
    for f in r.findings:
        by_port.setdefault((f.ip, f.port, f.protocol), []).append(f)
    out = []
    for d in r.devices:
        doors = []
        for p in d.open_ports:
            fs = sorted(by_port.get((d.ip, p["port"], p["protocol"]), []), key=lambda f: SEVERITY_ORDER[f.severity])
            risky = [f for f in fs if f.points > 0]
            proven = bool(risky) and all(
                verifications.get((f.ip, f.port, f.code), {}).get("status") == "resolved" for f in risky)
            if risky:
                sev = "resolved" if proven else risky[0].severity
                label = explain.get(risky[0].code, lang)["title"]
            elif fs:
                sev, label = "info", explain.get(fs[0].code, lang)["title"]
            else:
                sev, label = "none", p["service"] or "?"
            doors.append({"port": p["port"], "protocol": p["protocol"], "sev": sev, "label": label,
                          "icon": "✔" if sev == "resolved" else (explain.SEVERITY_ICON.get(sev, "🚪"))})
        doors.sort(key=lambda x: ({"high": 0, "medium": 1, "low": 2, "info": 3, "resolved": 4, "none": 5}[x["sev"]],
                                  x["port"]))
        unknown = any(f.code == "UNKNOWN_DEVICE" and f.ip == d.ip for f in r.findings)
        is_router = d.type_guess == "router" or d.ip.endswith(".1")
        out.append({
            "dev": d, "name": display_name(d, nick, lang), "nick": nick.get(d.device_id, ""),
            "icon": ICONS.get(d.type_guess, "❓"),
            "type": TYPE_RO.get(d.type_guess, d.type_guess) if lang == "ro" else d.type_guess,
            "doors": doors, "unknown": unknown, "router": is_router,
            "start_here": worst_dev is not None and d.ip == worst_dev.ip,
            "level": "high" if d.risk_points >= 20 else "medium" if d.risk_points >= 10 else
                     "low" if d.risk_points > 0 else "ok",
        })
    # front door (router) first, then most dangerous rooms
    out.sort(key=lambda x: (not x["router"], -x["dev"].risk_points, _ip_key(x["dev"].ip)))
    return out
