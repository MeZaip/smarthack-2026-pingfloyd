"""Builds the 'house map': each device is a room, each open port is a door."""
from __future__ import annotations

from ..core.models import _ip_key
from .views import SEVERITY_ORDER, Explain, ScanView

ICONS = {"router": "📡", "camera": "📷", "printer": "🖨️", "nas": "🗄️", "tv": "📺", "iot": "💡",
         "phone": "📱", "computer": "💻", "server": "🖥️", "unknown": "❓"}
_DOOR_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3, "none": 4}


def rooms(r: ScanView | None, lang: str, me_ip: str | None = None) -> list[dict]:
    """me_ip: the computer NetCheck runs on, highlighted as "this computer"."""
    if not r or not r.ok:
        return []
    worst = r.most_dangerous
    by_port: dict[tuple, list] = {}
    for f in r.findings:
        by_port.setdefault((f.ip, f.port, f.protocol), []).append(f)
    out = []
    for d in r.devices:
        doors = []
        for p in d.open_ports:
            fs = sorted(by_port.get((d.ip, p["port"], p["protocol"]), []), key=lambda f: SEVERITY_ORDER[f.severity])
            risky = [f for f in fs if f.points > 0]
            if risky:
                sev, label = risky[0].severity, Explain.get(risky[0].code, lang)["title"]
            elif fs:
                sev, label = "info", Explain.get(fs[0].code, lang)["title"]
            else:
                sev, label = "none", p["service"] or "?"
            doors.append({"port": p["port"], "protocol": p["protocol"], "sev": sev, "label": label,
                          "icon": Explain.SEVERITY_ICON.get(sev, "🚪")})
        doors.sort(key=lambda x: (_DOOR_ORDER[x["sev"]], x["port"]))
        out.append({
            "dev": d, "name": d.name, "icon": ICONS.get(d.type_guess, "❓"), "type": d.type_label,
            "doors": doors,
            "unknown": any(f.code == "UNKNOWN_DEVICE" and f.ip == d.ip for f in r.findings),
            "router": d.type_guess == "router",
            "me": me_ip is not None and d.ip == me_ip,
            "start_here": worst is not None and d.ip == worst.ip,
            "level": "high" if d.risk_points >= 20 else "medium" if d.risk_points >= 10 else
                     "low" if d.risk_points > 0 else "ok",
        })
    # front door (router) first, then the most dangerous rooms
    out.sort(key=lambda x: (not x["router"], -x["dev"].risk_points, _ip_key(x["dev"].ip)))
    return out
