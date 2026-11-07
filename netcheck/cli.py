"""Command line interface.

  python -m netcheck analyze <folder|file> [--out results]   -> findings.csv + scores.csv
  python -m netcheck report  <file> [--lang ro|en]           -> plain-language report in the terminal
  python -m netcheck ask     <file> "question" [--lang ro|en] [--previous <file>]
  python -m netcheck chat    <file> [--lang ro|en] [--previous <file>]   -> conversation with the assistant
  python -m netcheck diff    <before.xml> <after.xml> [--lang ro|en]
  python -m netcheck history add <file|folder>... | list | changes [--before ID --after ID] | delete [--yes]

Core Engine & CLI (netcheck/net/):
  python -m netcheck detect [--json]                              interface / subnet / gateway (FR-01)
  python -m netcheck scan [target] --confirm [--allow CIDR]       live scan of YOUR network (FR-02, FR-04)
  python -m netcheck parse <file|folder> [--out DIR]              §1 Raw Parsed Data JSON (data contract)
  python -m netcheck verify <scan.xml> <ip> <port> --confirm      „Dovedește!": re-check one fixed problem
  python -m netcheck watch --confirm [--interval 60]              „Paznic": alert on new device / new port

Web UI + JSON API (netcheck/web/):
  python -m netcheck serve [--port 8000]                          dashboard on http://127.0.0.1:8000 (no root)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core.analysis import analyze_file, analyze_folder, scan_files_in, write_results
from .core.device import DEVICE_LABELS
from .core.diff import compare
from .explain.texts import SEVERITY_LABELS, score_band, text_for


def _out(s: str = "") -> None:
    # Windows consoles may not be UTF-8; never crash on printing
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", "replace").decode("ascii"))


def cmd_analyze(args) -> int:
    from .core.analysis import skipped_files_in
    files = scan_files_in(args.path, args.all_files)
    if not files:
        _out(f"No .xml files found in {args.path}" + ("" if args.all_files else " (use --all-files to read every file)"))
        return 2
    results = analyze_folder(args.path, args.all_files)
    f_csv, s_csv = write_results(results, args.out)
    for r in results:
        status = f"score {r.score:>3}  findings {len(r.findings)}" if r.ok else f"ERROR: {r.error}"
        _out(f"{r.file:<40} {status}")
    skipped = [] if args.all_files else skipped_files_in(args.path)
    if skipped:
        _out(f"\n⚠ Not analysed (not .xml): {', '.join(skipped)}. If any of them is a scan file, "
             "re-run with --all-files so it gets its row (ERROR if unreadable).")
    _out(f"\nWrote {f_csv} and {s_csv}")
    return 0


def cmd_report(args) -> int:
    a = analyze_file(args.file)
    lang = args.lang
    if not a.ok:
        _out(("Fișierul nu poate fi citit: " if lang == "ro" else "The file cannot be read: ") + a.error)
        return 1
    band = score_band(a.score, lang)
    _out(f"{band['icon']}  {'Scor rețea' if lang == 'ro' else 'Network score'}: {a.score}/100 — {band['label']}")
    top = a.most_dangerous()
    if top:
        label = DEVICE_LABELS[top["type"]][lang]
        _out(("Cel mai periculos dispozitiv: " if lang == "ro" else "Most dangerous device: ")
             + f"{top['ip']} ({label}{', ' + top['vendor'] if top['vendor'] else ''})")
    _out()
    for i, f in enumerate(a.prioritized(), 1):
        t = text_for(f.code, lang)
        sev = SEVERITY_LABELS[f.severity]
        where = f"{f.ip}:{f.port}" if f.port is not None else f.ip
        _out(f"{i}. {sev['icon']} [{sev[lang]}] {t['title']} — {where}")
        _out(f"   {t['explain']}")
        for j, step in enumerate(t["steps"], 1):
            _out(f"     {j}) {step}")
        _out(f"   ({'dovadă' if lang == 'ro' else 'evidence'}: {f.evidence})")
        _out()
    if not a.findings:
        _out("Nu am găsit probleme." if lang == "ro" else "No problems found.")
    return 0


def cmd_ask(args) -> int:
    from .ai.assistant import ask
    a = analyze_file(args.file)
    if not a.ok:
        _out("ERROR: " + a.error)
        return 1
    prev = analyze_file(args.previous) if args.previous else None
    ans = ask(args.question, a, args.lang, prev)
    _out(ans.text)
    badge = "AI" if ans.source == "ai" else f"text încorporat / built-in ({ans.reason})"
    _out(f"\n[{badge}]")
    return 0


def cmd_chat(args) -> int:
    from .ai.assistant import Conversation
    a = analyze_file(args.file)
    if not a.ok:
        _out("ERROR: " + a.error)
        return 1
    prev = analyze_file(args.previous) if args.previous else None
    conv = Conversation(a, args.lang, prev)
    ro = args.lang == "ro"
    _out(("Întreabă orice despre această scanare. „nou” = conversație nouă, „gata” = ieșire." if ro else
          "Ask anything about this scan. 'new' = new conversation, 'quit' = exit."))
    while True:
        try:
            q = input("\n" + ("Tu: " if ro else "You: ")).strip()
        except (EOFError, KeyboardInterrupt):
            _out()
            return 0
        if q.lower() in ("gata", "exit", "quit", "q"):
            return 0
        if q.lower() in ("nou", "new"):
            conv.reset()
            _out("(conversație nouă)" if ro else "(new conversation)")
            continue
        if not q:
            continue
        ans = conv.ask(q)
        _out(("Asistent: " if ro else "Assistant: ") + ans.text)
        if ans.source != "ai":
            _out(f"[text încorporat / built-in ({ans.reason})]")


def cmd_diff(args) -> int:
    b, a = analyze_file(args.before), analyze_file(args.after)
    for r in (b, a):
        if not r.ok:
            _out(f"ERROR in {r.file}: {r.error}")
            return 1
    _out(json.dumps(compare(b, a), indent=2, ensure_ascii=False))
    return 0


def cmd_history_add(args) -> int:
    from . import history
    files = [f for path in args.paths for f in scan_files_in(path)]
    if not files:
        _out("No .xml files found.")
        return 2
    code = 0
    with history.open_history(args.db) as conn:
        for f in files:
            a = analyze_file(f)
            if not a.ok:
                _out(f"{a.file:<40} ERROR: {a.error} (not saved)")
                code = 1
                continue
            scan_id, created = history.save(conn, a)
            _out(f"{a.file:<40} score {a.score:>3}  " + (f"saved as #{scan_id}" if created else f"already saved (#{scan_id})"))
        ch = history.changes(conn)
    if ch and ch["alerts"]:
        _out("\n⚠ " + ", ".join(
            [f"new device {ip}" for ip in ch["new_devices"]]
            + [f"new open port {p['ip']}:{p['port']}/{p['protocol']}" for p in ch["new_port_alerts"]]))
    if ch:
        for u in ch["secured_ports"]:
            _out(f"✔ {u['ip']}: {u['service']} moved from port {u['from_port']} to secure port {u['to_port']}")
    _out(f"\nHistory: {history.db_path(args.db)}")
    return code


def cmd_history_list(args) -> int:
    from . import history
    with history.open_history(args.db) as conn:
        rows = history.trend(conn)
    if not rows:
        _out("No saved scans yet. Use: netcheck history add <scan.xml>")
        return 0
    prev = None
    for r in rows:
        delta = "" if prev is None else f"{r['network_score'] - prev:+d}"
        bar = "█" * (r["network_score"] // 5)
        _out(f"#{r['scan_id']:<3} {r['file']:<32} {r['network_score']:>3} {delta:>4}  {bar}"
             f"  ({r['devices']} devices, {r['findings']} findings)")
        prev = r["network_score"]
    return 0


def cmd_history_changes(args) -> int:
    from . import history
    with history.open_history(args.db) as conn:
        try:
            ch = history.changes(conn, args.before, args.after)
        except KeyError as e:
            _out(f"ERROR: {e.args[0]}")
            return 1
    if ch is None:
        _out("Need at least two saved scans.")
        return 1
    _out(json.dumps(ch, indent=2, ensure_ascii=False))
    return 0


def cmd_history_delete(args) -> int:
    from . import history
    path = history.db_path(args.db)
    if not args.yes:
        try:
            answer = input(f"Delete all saved scans in {path}? [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes", "d", "da"):
            _out("Nothing deleted.")
            return 1
    _out("History deleted." if history.delete_history(path) else "There was no history to delete.")
    return 0


# ---------------------------------------------------------------- Core Engine & CLI (netcheck/net/)
def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _refused(e, lang: str) -> int:
    _out("⛔ " + (e.message(lang) if hasattr(e, "message") else str(e)))
    return 3


def cmd_detect(args) -> int:
    from .net import netdetect
    try:
        n = netdetect.detect()
    except netdetect.NetworkDetectError as e:
        _out(f"✖ {e}")
        return 1
    if args.json:
        _out(_dump({"network": n.contract_network(), "interface": n.interface, "ip": n.ip}))
        return 0
    ro = args.lang == "ro"
    _out(f"{'interfață' if ro else 'interface'}: {n.interface}\n{'IP-ul tău' if ro else 'your IP'}:  {n.ip}\n"
         f"{'rețea' if ro else 'subnet'}:    {n.subnet}\n{'gateway'}:   {n.gateway or '?'}")
    return 0


def cmd_scan(args) -> int:
    from .core.parser import ScanFileError, parse_file
    from .net import contract, guardrail, netdetect, scanner
    try:
        net = netdetect.detect()
        allow = guardrail.build_allowlist(net.subnet, args.allow)
        target = guardrail.check_target(args.target or net.subnet, allow, confirmed=args.confirm)
    except guardrail.ScopeError as e:
        return _refused(e, args.lang)
    except netdetect.NetworkDetectError as e:
        if args.target:   # an explicit target is still judged: public / too large / no allowlist -> REFUSED
            try:
                guardrail.check_target(args.target, [], confirmed=True)
            except guardrail.ScopeError as se:
                return _refused(se, args.lang)
        _out(f"✖ {e}")
        return 3
    _out(("Scanez " if args.lang == "ro" else "Scanning ") + f"{target} (≤ {scanner.MAX_RATE} pkt/s). "
         + ("nmap are nevoie de drepturi de administrator; s-ar putea să-ți ceară parola."
            if args.lang == "ro" else "nmap needs admin rights; you may be asked for your password."))
    try:
        xml = scanner.run_scan(target, args.out)
    except scanner.ScanError as e:
        _out(f"✖ {e}")
        return 1
    raw_path = xml.with_suffix(".raw.json")
    try:  # §1 with the LIVE network facts (gateway is only known during a live scan)
        raw_path.write_text(_dump(contract.raw_scan(parse_file(xml), net.subnet, net.gateway)) + "\n",
                            encoding="utf-8")
    except ScanFileError:
        raw_path = None
    a = analyze_file(xml)
    status = f"score {a.score}/100, {len(a.findings)} findings" if a.ok else f"ERROR: {a.error}"
    _out(f"{xml.name}: {status}")
    if a.ok and not args.no_history:
        from . import history
        with history.open_history(args.db) as conn:
            scan_id, _ = history.save(conn, a)
        _out(f"history #{scan_id} (python -m netcheck history list)")
    _out(f"Saved {xml}" + (f" + {raw_path.name} (data contract §1)" if raw_path else ""))
    _out(f"Next: python -m netcheck report {xml}")
    return 0 if a.ok else 1


def cmd_parse(args) -> int:
    from .core.parser import ScanFileError, parse_file
    from .net import contract
    files = scan_files_in(args.path) if Path(args.path).exists() else []
    if not files:
        _out(f"✖ no .xml files found in {args.path}")
        return 2
    failed = 0
    for f in files:
        try:
            payload = contract.raw_scan(parse_file(f))
        except ScanFileError as e:
            print(f"✖ {f.name}: ERROR — {e}", file=sys.stderr)
            failed += 1
            continue
        if args.out:
            out = Path(args.out) / f"{payload['scan_id']}.raw.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(_dump(payload) + "\n", encoding="utf-8")
            _out(f"✔ {out}")
        else:
            _out(_dump(payload))
    return 1 if failed == len(files) else 0


def cmd_verify(args) -> int:
    from .net import guardrail, netdetect, verify
    if not args.confirm:
        _out("⛔ " + ("adaugă --confirm (confirmi că dispozitivul e al tău)" if args.lang == "ro"
                     else "add --confirm (you confirm you own this device)"))
        return 3
    a = analyze_file(args.scan)
    if not a.ok:
        _out(f"✖ {a.file}: ERROR — {a.error}")
        return 1
    proto = "udp" if args.udp else "tcp"
    targets = [f for f in a.findings if f.ip == args.ip and f.port == args.port and f.protocol == proto]
    if not targets:
        _out(f"✖ no finding for {args.ip}:{args.port}/{proto} in {a.file}")
        return 1
    try:
        allow = guardrail.build_allowlist(netdetect.detect().subnet, args.allow)
    except guardrail.ScopeError as e:
        return _refused(e, args.lang)
    except netdetect.NetworkDetectError as e:
        _out(f"✖ {e}")
        return 3
    host = next(h for h in a.scan.hosts if h.ip == args.ip)
    code = 0
    for f in targets:
        res = verify.verify(f, host, allow, allow_udp=args.udp)
        _out(f"{f.code} {f.ip}:{f.port} → {res.message(args.lang)}  [{res.evidence}]")
        code = max(code, 0 if res.status == "resolved" else 1)
    return code


def cmd_watch(args) -> int:
    from .net import guardrail, netdetect, watch
    if not args.confirm:
        _out("⛔ " + ("adaugă --confirm (confirmi că toate dispozitivele din rețea sunt ale tale)" if args.lang == "ro"
                     else "add --confirm (you confirm you own every device on this network)"))
        return 3
    try:
        return watch.run(interval=args.interval, lang=args.lang, extra_allow=args.allow)
    except guardrail.ScopeError as e:
        return _refused(e, args.lang)
    except netdetect.NetworkDetectError as e:
        _out(f"✖ {e}")
        return 3


def cmd_serve(args) -> int:
    try:
        import uvicorn
    except ImportError:
        _out("✖ The web UI needs extra packages: pip install -r requirements.txt")
        return 2
    if args.db:
        import os
        os.environ["NETCHECK_DB"] = args.db
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        import os
        os.environ["NETCHECK_ALLOW_ANY_HOST"] = "1"   # explicit opt-out of the local-host check (web/security.py)
        _out(f"⚠ Listening on {args.host}: anyone who can reach this address sees your scan results (no login).")
    _out(f"SafeHouse UI: http://{args.host}:{args.port}   (Ctrl+C to stop)")
    uvicorn.run("netcheck.web.app:app", host=args.host, port=args.port, log_level="warning")
    return 0


def cmd_app(args) -> int:
    from . import launcher
    return launcher.main(port=args.port, lang=args.lang, window=args.window, gateway=not args.no_gateway)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="netcheck", description="Secure Networks, Simply Explained")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("analyze", help="analyse a folder of nmap XML files and write the standard CSVs")
    s.add_argument("path")
    s.add_argument("--out", default="results")
    s.add_argument("--all-files", action="store_true",
                   help="read every (non-hidden) file in the folder, not only *.xml; unreadable ones get ERROR")
    s.set_defaults(fn=cmd_analyze)

    s = sub.add_parser("report", help="plain-language report for one scan file")
    s.add_argument("file")
    s.add_argument("--lang", choices=["ro", "en"], default="ro")
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("ask", help="ask the assistant a question about one scan")
    s.add_argument("file")
    s.add_argument("question")
    s.add_argument("--lang", choices=["ro", "en"], default="ro")
    s.add_argument("--previous", help="previous scan of the same network, for 'what changed?' questions")
    s.set_defaults(fn=cmd_ask)

    s = sub.add_parser("chat", help="have a conversation with the assistant about one scan")
    s.add_argument("file")
    s.add_argument("--lang", choices=["ro", "en"], default="ro")
    s.add_argument("--previous", help="previous scan of the same network")
    s.set_defaults(fn=cmd_chat)

    s = sub.add_parser("diff", help="compare two scans of the same network")
    s.add_argument("before")
    s.add_argument("after")
    s.set_defaults(fn=cmd_diff)

    h = sub.add_parser("history", help="local scan history: score trend, before/after, delete")
    hsub = h.add_subparsers(dest="history_cmd", required=True)
    db_help = "history database (default: $NETCHECK_DB or ~/.netcheck/history.sqlite)"

    s = hsub.add_parser("add", help="analyse scan file(s) and save them to the history")
    s.add_argument("paths", nargs="+")
    s.add_argument("--db", help=db_help)
    s.set_defaults(fn=cmd_history_add)

    s = hsub.add_parser("list", help="score trend of all saved scans")
    s.add_argument("--db", help=db_help)
    s.set_defaults(fn=cmd_history_list)

    s = hsub.add_parser("changes", help="before/after between saved scans (default: the last two)")
    s.add_argument("--before", type=int, help="scan id")
    s.add_argument("--after", type=int, help="scan id")
    s.add_argument("--db", help=db_help)
    s.set_defaults(fn=cmd_history_changes)

    s = hsub.add_parser("delete", help="delete my history (removes the database file)")
    s.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    s.add_argument("--db", help=db_help)
    s.set_defaults(fn=cmd_history_delete)

    # ---- Core Engine & CLI
    s = sub.add_parser("detect", help="show the network you are connected to (FR-01)")
    s.add_argument("--json", action="store_true", help="print the data-contract 'network' object")
    s.add_argument("--lang", choices=["ro", "en"], default="ro")
    s.set_defaults(fn=cmd_detect)

    s = sub.add_parser("scan", help="live scan of YOUR network (needs --confirm; sudo only for nmap)")
    s.add_argument("target", nargs="?", help="IP/CIDR inside your subnet (default: the connected subnet)")
    s.add_argument("--confirm", action="store_true", help="I own every device on this network")
    s.add_argument("--allow", action="append", default=[], help="extra PRIVATE CIDR to allow (repeatable)")
    s.add_argument("--out", default="scans")
    s.add_argument("--no-history", action="store_true", help="do not save the result to the local history")
    s.add_argument("--db", help="history database (default: $NETCHECK_DB or ~/.netcheck/history.sqlite)")
    s.add_argument("--lang", choices=["ro", "en"], default="ro")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("parse", help="nmap XML -> §1 Raw Parsed Data JSON (offline, no root)")
    s.add_argument("path", help="XML file or folder")
    s.add_argument("--out", help="folder for <scan_id>.raw.json (default: print to stdout)")
    s.set_defaults(fn=cmd_parse)

    s = sub.add_parser("verify", help="„Dovedește!”: re-check one fixed problem from a scan file")
    s.add_argument("scan", help="the nmap XML that showed the problem")
    s.add_argument("ip")
    s.add_argument("port", type=int)
    s.add_argument("--udp", action="store_true", help="UDP port (needs admin rights)")
    s.add_argument("--confirm", action="store_true")
    s.add_argument("--allow", action="append", default=[])
    s.add_argument("--lang", choices=["ro", "en"], default="ro")
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("watch", help="„Paznic”: notify me about new devices / newly opened ports (no root)")
    s.add_argument("--confirm", action="store_true")
    s.add_argument("--interval", type=int, default=60, help="seconds between checks")
    s.add_argument("--allow", action="append", default=[])
    s.add_argument("--lang", choices=["ro", "en"], default="ro")
    s.set_defaults(fn=cmd_watch)

    s = sub.add_parser("serve", help="web UI + JSON API on this computer only (no root)")
    s.add_argument("--host", default="127.0.0.1",
                   help="address to listen on (default 127.0.0.1). The UI has no login and shows your "
                        "network's weak spots: prefer a private interface (e.g. your Tailscale IP) over 0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--db", help="history database (default: $NETCHECK_DB or ~/.netcheck/history.sqlite)")
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("app", help="start SafeHouse for a normal user: app window, no terminal needed")
    s.add_argument("--port", type=int, default=0, help="default: a free port")
    s.add_argument("--lang", choices=["ro", "en"], default="ro")
    s.add_argument("--window", choices=["auto", "window", "app", "browser"], default="auto",
                   help="auto: own window (pywebview) or Edge/Chrome app window, else the browser")
    s.add_argument("--no-gateway", action="store_true", help="do not start a local AI gateway")
    s.set_defaults(fn=cmd_app)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
