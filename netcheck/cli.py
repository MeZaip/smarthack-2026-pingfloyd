"""Command line entry point.

  netcheck analyze <folder|file> [--out results] [--history]   offline, no network, no root
  netcheck detect                                               show interface / subnet / gateway
  netcheck scan [target] --confirm [--allow CIDR]               live scan (guardrail + sudo for nmap only)
  netcheck chat [--scan file.xml] [--guide] [--lang ro|en]      AI assistant (offline fallback)
  netcheck serve [--port 8000]                                  web UI on http://127.0.0.1:8000
  netcheck history [--delete]                                   list or delete local history
  netcheck verify <ip> <port> --confirm [--udp]                 „Dovedește!”: re-check one fix
  netcheck cert --before ID --after ID [--out f.json]           signed before/after certificate
  netcheck cert-verify f.json                                   detect a forged certificate
  netcheck watch --confirm [--interval 60]                      „Paznic”: alerts for new devices/ports
  netcheck ai-status                                            which AI is active (local Ollama by default)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import explain, guardrail, history, netdetect
from .analyzer import analyze_file, analyze_folder, most_dangerous, ranked_findings, write_csvs


def _print_result(r, lang: str) -> None:
    if not r.ok:
        print(f"✖ {r.file}: ERROR — {r.error}")
        return
    band = explain.score_band(r.score, lang)
    print(f"\n{r.file}: score {r.score}/100 {band[1]} {band[2]}  ({len(r.devices)} devices, {len(r.findings)} findings)")
    dev, first = most_dangerous(r)
    if dev:
        t = explain.get(first.code, lang)
        print(f"  ➜ {'Repară primul' if lang == 'ro' else 'Fix first'}: {dev.ip} — {t['title']}: {t['steps'][0]}")
    for f in ranked_findings(r):
        port = "" if f.port is None else f":{f.port}"
        print(f"  {explain.SEVERITY_ICON[f.severity]} {f.severity:<6} {f.ip}{port:<7} {f.code}")


def cmd_analyze(a) -> int:
    target = Path(a.path)
    if target.is_dir():
        results = analyze_folder(target, all_files=a.all_files)
    elif target.is_file():
        results = [analyze_file(target)]
    else:
        print(f"✖ not found: {target}", file=sys.stderr)
        return 2
    fp, sp = write_csvs(results, a.out)
    for r in results:
        _print_result(r, a.lang)
        if a.history:
            history.save(r, source=a.source or (target.name if target.is_dir() else "lab"))
    print(f"\nWrote {fp} and {sp}  ({sum(len(r.findings) for r in results)} findings, {len(results)} files)")
    return 0


def cmd_detect(a) -> int:
    try:
        n = netdetect.detect()
    except netdetect.NetworkDetectError as e:
        print(f"✖ {e}")
        return 1
    print(f"interface: {n.interface}\nyour IP:   {n.ip}\nsubnet:    {n.subnet}\ngateway:   {n.gateway}")
    return 0


def cmd_scan(a) -> int:
    from . import scanner
    try:
        net = netdetect.detect()
        allow = guardrail.build_allowlist(net.subnet, a.allow)
        target = guardrail.check_target(a.target or net.subnet, allow, confirmed=a.confirm)
    except (guardrail.ScopeError, netdetect.NetworkDetectError) as e:
        print(f"⛔ {e}")
        return 3
    print(f"Scanning {target} (rate ≤ {scanner.MAX_RATE} pkt/s). nmap needs admin rights; you may be asked for your password.")
    try:
        xml = scanner.run_scan(target, a.out)
    except scanner.ScanError as e:
        print(f"✖ {e}")
        return 1
    r = analyze_file(xml)
    sid = history.save(r, "lab")
    _print_result(r, a.lang)
    prev = history.previous_of(sid)
    if prev:
        d = history.diff(history.load(prev), r)
        print(f"\nvs previous scan: score {d['old_score']} → {d['new_score']}, "
              f"{len(d['resolved_findings'])} resolved, {len(d['new_findings'])} new")
        for msg in history.alerts(d, a.lang):
            print("  🔔 " + msg)
    print(f"\nSaved {xml}")
    return 0


def cmd_history(a) -> int:
    if a.delete:
        history.delete_all()
        print("History deleted." if a.lang == "en" else "Istoricul a fost șters.")
        return 0
    for s in history.list_scans():
        print(f"#{s['id']:<4} {s['created_at']}  {s['source']:<20} {s['file']:<30} {s['score'] if s['ok'] else 'ERROR'}")
    return 0


def cmd_serve(a) -> int:
    import uvicorn
    print(f"NetCheck UI on http://127.0.0.1:{a.port}  (local only)")
    uvicorn.run("netcheck.web.app:app", host="127.0.0.1", port=a.port, log_level="warning")
    return 0


def cmd_verify(a) -> int:
    from . import verify
    from .models import Host
    if not a.confirm:
        print("⛔ add --confirm (you confirm you own this device)")
        return 3
    sid = a.scan or history.latest_id()
    r = history.load(sid) if sid else None
    proto = "udp" if a.udp else "tcp"
    fs = [f for f in (r.findings if r and r.ok else []) if f.ip == a.ip and f.port == a.port and f.protocol == proto]
    if not fs:
        print(f"✖ no finding for {a.ip}:{a.port}/{proto} in scan #{sid}. Run a scan first (netcheck scan --confirm).")
        return 1
    d = next(x for x in r.devices if x.ip == a.ip)
    try:
        allow = guardrail.build_allowlist(netdetect.detect().subnet, a.allow)
    except (guardrail.ScopeError, netdetect.NetworkDetectError) as e:
        print(f"⛔ {e}")
        return 3
    worst = 0
    for f in fs:
        res = verify.verify(f, Host(ip=d.ip, vendor=d.vendor, hostname=d.hostname), scan_id=sid,
                            device_id=d.device_id, allowlist=allow, allow_udp=a.udp)
        print(f"{f.code} {f.ip}:{f.port} → {res.message(a.lang)}  [{res.evidence}]")
        worst = max(worst, 0 if res.status == "resolved" else 1)
    return worst


def cmd_cert(a) -> int:
    import json as _json
    from . import certificate
    metas = {s["id"]: s for s in history.list_scans()}
    b, af = history.load(a.before), history.load(a.after)
    if not (b and af and b.ok and af.ok):
        print("✖ both scans must exist and be readable (see: netcheck history)")
        return 1
    cert = certificate.build(b, af, metas[a.before]["created_at"], metas[a.after]["created_at"])
    Path(a.out).write_text(_json.dumps(cert, ensure_ascii=False, indent=2), encoding="utf-8")
    p = cert["payload"]
    print(f"📜 {a.out}: score {p['before']['score']} → {p['after']['score']}, {len(p['resolved'])} resolved. "
          f"Key fingerprint {cert['key_fingerprint']}")
    return 0


def cmd_cert_verify(a) -> int:
    import json as _json
    from . import certificate
    try:
        cert = _json.loads(Path(a.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"⛔ cannot read certificate: {e}")
        return 1
    ok, reason, ours = certificate.verify(cert)
    if ok:
        print(f"✔ VALID — {reason}. " + ("Issued by this computer." if ours else
                                         f"Issued by another computer, key {cert.get('key_fingerprint')}."))
        return 0
    print(f"⛔ INVALID — {reason}")
    return 2


def cmd_watch(a) -> int:
    from . import watch
    if not a.confirm:
        print("⛔ add --confirm (you confirm you own every device on this network)")
        return 3
    try:
        return watch.run(interval=a.interval, lang=a.lang, extra_allow=a.allow)
    except (guardrail.ScopeError, netdetect.NetworkDetectError) as e:
        print(f"⛔ {e}")
        return 3


def cmd_ai_status(a) -> int:
    from . import llm
    print(llm.status_report())
    return 0


def cmd_chat(a) -> int:
    from .chat import run_chat
    return run_chat(scan=a.scan, lang=a.lang, guide=a.guide, allow=a.allow)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="netcheck", description="Secure Networks, Simply Explained")
    p.add_argument("--lang", choices=["ro", "en"], default="ro")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("analyze", help="analyse nmap XML file(s) offline and write findings.csv + scores.csv")
    s.add_argument("path")
    s.add_argument("--out", default="results")
    s.add_argument("--history", action="store_true", help="also save results to local history")
    s.add_argument("--source", help="history group name (default: folder name)")
    s.add_argument("--all-files", action="store_true", help="include files without .xml extension")
    s.set_defaults(fn=cmd_analyze)

    s = sub.add_parser("detect", help="show the network you are connected to")
    s.set_defaults(fn=cmd_detect)

    s = sub.add_parser("scan", help="live scan of YOUR network (needs --confirm)")
    s.add_argument("target", nargs="?", help="IP/CIDR inside your subnet (default: connected subnet)")
    s.add_argument("--confirm", action="store_true", help="I own every device on this network")
    s.add_argument("--allow", action="append", default=[], help="extra private CIDR to allow (repeatable)")
    s.add_argument("--out", default="scans")
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("chat", help="talk to the assistant (AI if ANTHROPIC_API_KEY is set, else offline)")
    s.add_argument("--scan", help="nmap XML file to load")
    s.add_argument("--guide", action="store_true", help="step-by-step guided check-up")
    s.add_argument("--allow", action="append", default=[])
    s.set_defaults(fn=cmd_chat)

    s = sub.add_parser("serve", help="start the web UI")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("verify", help="„Dovedește!”: re-check one fixed problem (ip port)")
    s.add_argument("ip")
    s.add_argument("port", type=int)
    s.add_argument("--udp", action="store_true", help="UDP port (needs admin rights)")
    s.add_argument("--scan", type=int, help="history scan id (default: latest)")
    s.add_argument("--confirm", action="store_true")
    s.add_argument("--allow", action="append", default=[])
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("cert", help="create a signed before/after certificate")
    s.add_argument("--before", type=int, required=True, help="history id of the 'before' scan")
    s.add_argument("--after", type=int, required=True, help="history id of the 'after' scan")
    s.add_argument("--out", default="certificate.json")
    s.set_defaults(fn=cmd_cert)

    s = sub.add_parser("cert-verify", help="check a certificate was not altered")
    s.add_argument("file")
    s.set_defaults(fn=cmd_cert_verify)

    s = sub.add_parser("watch", help="„Paznic”: notify me about new devices / new open ports")
    s.add_argument("--confirm", action="store_true")
    s.add_argument("--interval", type=int, default=60, help="seconds between checks")
    s.add_argument("--allow", action="append", default=[])
    s.set_defaults(fn=cmd_watch)

    s = sub.add_parser("ai-status", help="show which AI is active (local Ollama / Claude / offline)")
    s.set_defaults(fn=cmd_ai_status)

    s = sub.add_parser("history", help="list or delete local history")
    s.add_argument("--delete", action="store_true")
    s.set_defaults(fn=cmd_history)

    a = p.parse_args(argv)
    return a.fn(a)
