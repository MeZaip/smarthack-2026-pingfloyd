"""Command line interface.

  python -m netcheck analyze <folder|file> [--out results]   -> findings.csv + scores.csv
  python -m netcheck report  <file> [--lang ro|en]           -> plain-language report in the terminal
  python -m netcheck ask     <file> "question" [--lang ro|en] [--previous <file>]
  python -m netcheck diff    <before.xml> <after.xml> [--lang ro|en]
  python -m netcheck history add <file|folder>... | list | changes [--before ID --after ID] | delete [--yes]
"""
from __future__ import annotations

import argparse
import json
import sys

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
    files = scan_files_in(args.path)
    if not files:
        _out(f"No .xml files found in {args.path}")
        return 2
    results = analyze_folder(args.path)
    f_csv, s_csv = write_results(results, args.out)
    for r in results:
        status = f"score {r.score:>3}  findings {len(r.findings)}" if r.ok else f"ERROR: {r.error}"
        _out(f"{r.file:<40} {status}")
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
            + [f"new open port {p['ip']}:{p['port']}/{p['protocol']}" for p in ch["opened_ports"]]))
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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="netcheck", description="Secure Networks, Simply Explained")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("analyze", help="analyse a folder of nmap XML files and write the standard CSVs")
    s.add_argument("path")
    s.add_argument("--out", default="results")
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

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
