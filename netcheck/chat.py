"""Interactive terminal assistant: `netcheck chat` and `netcheck chat --guide`."""
from __future__ import annotations

from pathlib import Path

from . import explain, guardrail, history, netdetect
from .analyzer import most_dangerous
from .assistant import Assistant, Session, tool_live_scan

YES = {"da", "d", "yes", "y", "ok", "gata", "done"}

T = {
    "ro": {
        "hello": "👋 Salut! Sunt NetCheck. Te ajut să înțelegi și să repari rețeaua ta.",
        "mode_ai": "Mod: AI — {p}. Răspunsurile sunt verificate automat față de scanare.",
        "mode_off": "Mod: offline, texte integrate ({p}). Vezi: python -m netcheck ai-status",
        "cmds": "Comenzi: load <fișier.xml> · scan · guide · lang en · history · exit. Sau întreabă orice despre rețea.",
        "bye": "La revedere! Rescanează după fiecare reparație ca să vezi scorul crescând.",
        "loaded": "Am încărcat {f}: scor {s}/100 {i} {l}.",
        "load_err": "Fișierul {f} nu poate fi citit: {e}",
        "g1": "Pasul 1/6 — Caut rețeaua la care ești conectat…",
        "g1_ok": "Ești pe interfața {iface}, adresa ta {ip}, rețeaua {net}, routerul/telefonul {gw}.",
        "g2": "Pasul 2/6 — Pot scana DOAR această rețea ({net}), cu maxim 100 pachete/secundă. "
              "Nu ghicim parole și nu atacăm nimic — doar vedem ce „uși” sunt deschise.",
        "g2_file": "Sau, dacă ai deja un fișier de scanare, scrie calea lui (ex: scans/scan_01.xml). Enter = scanare live.",
        "g3": "Pasul 3/6 — Rezultat:",
        "g4": "Pasul 4/6 — Cel mai periculos dispozitiv: {ip} ({name}). Repară primul:",
        "g4_none": "Pasul 4/6 — Nu am găsit probleme. Bravo! 🎉",
        "g5": "Pasul 5/6 — Fă pașii de mai sus. Poți să-mi pui întrebări între timp. Scrie „gata” când ai terminat.",
        "g6": "Pasul 6/6 — Rescanez ca să verificăm…",
        "g6_file": "Scrie calea fișierului nou de scanare (sau Enter pentru scanare live):",
        "g_done": "Ghid terminat. Scor: {a} → {b}. Poți continua să întrebi.",
        "refused": "⛔ {e}",
        "ask": "tu> ",
    },
    "en": {
        "hello": "👋 Hi! I'm NetCheck. I help you understand and fix your network.",
        "mode_ai": "Mode: AI — {p}. Answers are automatically checked against the scan.",
        "mode_off": "Mode: offline, built-in texts ({p}). See: python -m netcheck ai-status",
        "cmds": "Commands: load <file.xml> · scan · guide · lang ro · history · exit. Or ask anything about your network.",
        "bye": "Bye! Re-scan after every fix to see your score go up.",
        "loaded": "Loaded {f}: score {s}/100 {i} {l}.",
        "load_err": "The file {f} cannot be read: {e}",
        "g1": "Step 1/6 — Looking for the network you are connected to…",
        "g1_ok": "You are on interface {iface}, your address {ip}, network {net}, router/phone {gw}.",
        "g2": "Step 2/6 — I can scan ONLY this network ({net}), at most 100 packets/second. "
              "We never guess passwords or attack anything — we only look at which 'doors' are open.",
        "g2_file": "Or, if you already have a scan file, type its path (e.g. scans/scan_01.xml). Enter = live scan.",
        "g3": "Step 3/6 — Result:",
        "g4": "Step 4/6 — Most dangerous device: {ip} ({name}). Fix this first:",
        "g4_none": "Step 4/6 — No problems found. Well done! 🎉",
        "g5": "Step 5/6 — Do the steps above. You can ask me questions meanwhile. Type \"done\" when finished.",
        "g6": "Step 6/6 — Re-scanning to check…",
        "g6_file": "Type the path of the new scan file (or Enter for a live scan):",
        "g_done": "Guide finished. Score: {a} → {b}. Keep asking if you like.",
        "refused": "⛔ {e}",
        "ask": "you> ",
    },
}


def _confirm(question: str) -> bool:
    try:
        return input("❓ " + question).strip().lower() in YES
    except EOFError:
        return False


def _show_loaded(s: Session) -> None:
    t = T[s.lang]
    r = s.result
    if r is None:
        return
    if not r.ok:
        print(t["load_err"].format(f=r.file, e=r.error))
        return
    c, icon, label = explain.score_band(r.score, s.lang)
    print(t["loaded"].format(f=r.file, s=r.score, i=icon, l=label))


def _get_scan(s: Session, a: Assistant, prompt_key: str) -> bool:
    """Ask for a file path or run a guarded live scan. Returns True if a scan is loaded."""
    t = T[s.lang]
    print(t[prompt_key])
    try:
        path = input("> ").strip()
    except EOFError:
        return False
    if path:
        if not Path(path).is_file():
            print("✖", path)
            return False
        s.load_file(path)
        _show_loaded(s)
        return s.result is not None and s.result.ok
    out = tool_live_scan(s)
    if "refused" in out or "error" in out:
        print(t["refused"].format(e=out.get("refused") or out.get("error")))
        return False
    _show_loaded(s)
    return True


def run_guide(s: Session, a: Assistant) -> None:
    t = T[s.lang]
    print("\n" + t["g1"])
    try:
        n = netdetect.detect()
        print(t["g1_ok"].format(iface=n.interface, ip=n.ip, net=n.subnet, gw=n.gateway or "?"))
        net = n.subnet
    except netdetect.NetworkDetectError as e:
        print(t["refused"].format(e=e))
        net = "?"
    print("\n" + t["g2"].format(net=net))
    if not _get_scan(s, a, "g2_file"):
        return
    before = s.result.score
    print("\n" + t["g3"])
    print(a.ask("Rezumă scanarea în 3 rânduri." if s.lang == "ro" else "Summarise the scan in 3 lines."))
    dev, first = most_dangerous(s.result)
    if not dev:
        print("\n" + t["g4_none"])
        return
    print("\n" + t["g4"].format(ip=dev.ip, name=dev.hostname or dev.vendor or dev.type_guess))
    fx = explain.get(first.code, s.lang)
    print(f"{explain.SEVERITY_ICON[first.severity]} {fx['title']}\n{fx['explain']}")
    for i, step in enumerate(fx["steps"], 1):
        print(f"  {i}. {step}")
    print("\n" + t["g5"])
    while True:
        try:
            q = input(t["ask"]).strip()
        except EOFError:
            return
        if q.lower() in YES:
            break
        if q.lower() in {"exit", "quit", "iesire", "ieșire"}:
            return
        if q:
            print(a.ask(q))
    print("\n" + t["g6"])
    if not _get_scan(s, a, "g6_file"):
        return
    print(t["g_done"].format(a=before, b=s.result.score))
    print(a.ask("Ce s-a schimbat față de scanarea anterioară?" if s.lang == "ro"
                else "What changed compared with the previous scan?"))


def run_chat(scan: str | None, lang: str, guide: bool, allow: list[str]) -> int:
    s = Session(lang=lang, allow_live_scan=True, confirm=_confirm, extra_allow=allow)
    a = Assistant(s)
    t = T[lang]
    print(t["hello"])
    print((t["mode_ai"] if a.online else t["mode_off"]).format(p=a.status))
    print(t["cmds"])
    if scan:
        s.load_file(scan)
        _show_loaded(s)
    elif history.latest_id():
        s.load_history(history.latest_id())
        _show_loaded(s)
    if guide:
        run_guide(s, a)
    while True:
        try:
            q = input("\n" + T[s.lang]["ask"]).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        low = q.lower()
        if low in {"exit", "quit", "iesire", "ieșire", "q"}:
            break
        if low.startswith("load "):
            path = q[5:].strip()
            if Path(path).is_file():
                s.load_file(path)
                _show_loaded(s)
            else:
                print("✖", path)
            continue
        if low in {"lang en", "lang ro"}:
            s.lang = low[-2:]
            print(T[s.lang]["cmds"])
            continue
        if low in {"guide", "ghid"}:
            run_guide(s, a)
            continue
        if low in {"history", "istoric"}:
            for row in history.list_scans()[-10:]:
                print(f"#{row['id']} {row['created_at']} {row['file']} → {row['score'] if row['ok'] else 'ERROR'}")
            continue
        if low in {"scan", "scaneaza", "scanează"} and not a.online:
            out = tool_live_scan(s)
            if "refused" in out or "error" in out:
                print(T[s.lang]["refused"].format(e=out.get("refused") or out.get("error")))
            else:
                _show_loaded(s)
            continue
        print(a.ask(q))
    print(T[s.lang]["bye"])
    return 0
