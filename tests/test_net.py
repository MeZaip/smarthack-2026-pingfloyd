"""Core Engine & CLI (netcheck/net/ + core/parser.py): guardrail, network detection, scanner,
data contract §1, „Dovedește!" (verify), „Paznic" (watch) and the CLI commands."""
import json
import re
import stat
from pathlib import Path

import pytest

from netcheck import cli
from netcheck.core.analysis import analyze_folder, write_results
from netcheck.core.models import Finding, Host, Port
from netcheck.core.parser import ScanFileError, parse_bytes, parse_file
from netcheck.core.rules import evaluate
from netcheck.net import contract, guardrail, netdetect, scanner, verify, watch

REPO = Path(__file__).parent.parent
FIX = Path(__file__).parent / "fixtures" / "synthetic"
GOOD = sorted(p for p in FIX.glob("*.xml") if "broken" not in p.name)
NMAP_HEAD = (b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE nmaprun>\n'
             b'<?xml-stylesheet href="file:///usr/share/nmap/nmap.xsl" type="text/xsl"?>\n')


@pytest.fixture(autouse=True)
def private_home(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "home" / "history.sqlite"))
    monkeypatch.delenv("NETCHECK_ALLOWLIST", raising=False)


def _with_real_nmap_header(xml: bytes) -> bytes:
    # replace whatever header the fixture has (it may already be the real nmap one) by exactly NMAP_HEAD
    body = re.sub(rb"^<\?xml[^>]*\?>\s*(<!DOCTYPE nmaprun>\s*)?(<\?xml-stylesheet[^>]*\?>\s*)?", b"", xml)
    return NMAP_HEAD + body


# ------------------------------------------------------------------ parser: real nmap files
@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_real_nmap_doctype_is_accepted_with_identical_findings(path):
    """Real `nmap -oX` output always contains <!DOCTYPE nmaprun>; it must not become ERROR."""
    key = lambda fs: [(f.ip, f.port, f.code, f.severity) for f in fs]  # noqa: E731
    assert key(evaluate(parse_bytes(_with_real_nmap_header(path.read_bytes())))) == key(evaluate(parse_file(path)))


@pytest.mark.parametrize("payload", [
    b'<?xml version="1.0"?><!DOCTYPE nmaprun [<!ENTITY x SYSTEM "file:///etc/passwd">]><nmaprun>&x;</nmaprun>',
    b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;">]><nmaprun>&b;</nmaprun>',
    b'<?xml version="1.0"?><!DOCTYPE nmaprun [<!ELEMENT nmaprun ANY>]><nmaprun/>',
    b'<?xml version="1.0"?><!DOCTYPE nmaprun SYSTEM "http://evil.example/x.dtd"><nmaprun/>',
    b'<?xml version="1.0"?><!DOCTYPE nmaprun><!DOCTYPE nmaprun><nmaprun/>',
])
def test_hostile_dtd_still_refused(payload):
    with pytest.raises(ScanFileError):
        parse_bytes(payload)


# ------------------------------------------------------------------ guardrail
ALLOW = guardrail.build_allowlist("172.20.10.0/28")


@pytest.mark.parametrize("target", ["8.8.8.8", "1.1.1.0/24", "100.64.1.1", "10.0.0.0/8", "192.168.50.0/24",
                                    "127.0.0.1", "224.0.0.1", "169.254.1.1", "not-an-ip", "172.20.10.0/27"])
def test_guardrail_refuses(target):
    with pytest.raises(guardrail.ScopeError):
        guardrail.check_target(target, ALLOW, confirmed=True)


def test_guardrail_confirm_and_languages():
    with pytest.raises(guardrail.ScopeError) as e:
        guardrail.check_target("172.20.10.0/28", ALLOW, confirmed=False)
    assert "--confirm" in e.value.message("en") and "--confirm" in e.value.message("ro")
    assert "acordul" in e.value.message("ro")
    with pytest.raises(guardrail.ScopeError) as e:
        guardrail.check_target("8.8.8.8", ALLOW, confirmed=True)
    assert e.value.message("ro").startswith("REFUZAT") and str(e.value).startswith("REFUSED")
    assert guardrail.check_target("172.20.10.5", ALLOW, confirmed=True) == "172.20.10.5/32"


def test_allowlist_rejects_public_extra():
    with pytest.raises(guardrail.ScopeError):
        guardrail.build_allowlist("172.20.10.0/28", ["8.8.8.0/24"])
    assert len(guardrail.build_allowlist("172.20.10.0/28", ["192.168.77.0/24"])) == 2


# ------------------------------------------------------------------ network detection
MAC_ROUTE = "   route to: default\ndestination: default\n    gateway: 172.20.10.1\n  interface: en0\n"
MAC_IFCONFIG = "en0: flags=8863<UP>\n\tinet 172.20.10.2 netmask 0xfffffff0 broadcast 172.20.10.15\n"
LINUX_ROUTE = "default via 192.168.43.1 dev wlan0 proto dhcp metric 600\n"
LINUX_ADDR = "3: wlan0    inet 192.168.43.17/24 brd 192.168.43.255 scope global dynamic wlan0\n"


def test_netdetect_parsers():
    assert netdetect.parse_macos_route(MAC_ROUTE) == ("172.20.10.1", "en0")
    assert netdetect.parse_ifconfig(MAC_IFCONFIG) == ("172.20.10.2", "255.255.255.240")
    assert netdetect.parse_linux_route(LINUX_ROUTE) == ("192.168.43.1", "wlan0")
    assert netdetect.parse_ip_addr(LINUX_ADDR) == ("192.168.43.17", "255.255.255.0")


def test_detect_without_psutil_iphone_hotspot(monkeypatch):
    monkeypatch.setattr(netdetect.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(netdetect, "_addr_psutil", lambda iface: None)
    monkeypatch.setattr(netdetect, "_run", lambda cmd: MAC_ROUTE if cmd[0] == "route" else MAC_IFCONFIG)
    n = netdetect.detect()
    assert (n.interface, n.ip, n.subnet, n.gateway) == ("en0", "172.20.10.2", "172.20.10.0/28", "172.20.10.1")
    assert n.contract_network() == {"subnet": "172.20.10.0/28", "gateway": "172.20.10.1"}


# ------------------------------------------------------------------ scanner
def test_top_ports_from_nmap_services(tmp_path):
    svc = tmp_path / "nmap-services"
    svc.write_text("# comment\nhttp\t80/tcp\t0.48\ntelnet\t23/tcp\t0.22\nsnmp\t161/udp\t0.43\nfoo\t9999/tcp\t0.0001\n")
    assert scanner.top_tcp_ports(2, [str(svc)]) == "23,80"


def test_scan_command_follows_rules_of_engagement(tmp_path):
    cmd = scanner.build_command("172.20.10.0/28", tmp_path / "x.xml")
    assert {"-sS", "-sU", "-sV"} <= set(cmd) and cmd[-1] == "172.20.10.0/28"
    assert cmd[cmd.index("--max-rate") + 1] == "100"
    assert cmd[cmd.index("--script") + 1] == "http-title"
    assert cmd[cmd.index("-p") + 1].endswith(",U:53,123,161,1900,5353")
    assert "sudo" not in cmd  # sudo is added only when actually running


# ------------------------------------------------------------------ data contract §1
def _contract_example(n: int) -> dict:
    text = (REPO / "service_data_contracts.md").read_text(encoding="utf-8")
    return json.loads(re.findall(r"```json\n(.*?)```", text, re.S)[n])


def _same_keys(ours, example, path="$"):
    if isinstance(example, dict):
        assert isinstance(ours, dict) and list(ours) == list(example), f"{path}: {list(ours)} != {list(example)}"
        for k in example:
            _same_keys(ours[k], example[k], f"{path}.{k}")
    elif isinstance(example, list) and example and ours:
        for item in ours:
            _same_keys(item, example[0], f"{path}[]")


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_raw_payload_matches_contract(path):
    _same_keys(contract.raw_scan(parse_file(path)), _contract_example(0))


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_rules_give_same_findings_from_contract(path):
    """§1 carries everything the Rule Engine needs."""
    from netcheck.core.models import ScanResult
    key = lambda fs: [(f.ip, f.port, f.code, f.severity) for f in fs]  # noqa: E731
    payload = json.loads(json.dumps(contract.raw_scan(parse_file(path))))
    assert key(evaluate(ScanResult(source=path.name, hosts=contract.hosts_from_raw(payload)))) == \
        key(evaluate(parse_file(path)))


def test_contract_details():
    raw = contract.raw_scan(parse_file(FIX / "V1_home_basic.xml"))
    ports = {p["port"]: p for d in raw["devices"] for p in d["open_ports"]}
    assert ports[443]["service"] == "ssl/http" and ports[80]["service"] == "http"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", raw["timestamp"] or "2000-01-01T00:00:00Z")
    assert raw["network"]["gateway"] is None
    assert contract.mask_mac("14:cc:20:11:1a:2b") == "XX:XX:XX:XX:1A:2B" and contract.mask_mac(None) is None
    live = contract.raw_scan(parse_file(FIX / "V1_home_basic.xml"), "192.168.1.0/24", "192.168.1.1")
    gw = next(d for d in live["devices"] if d["ip"] == "192.168.1.1")
    assert live["network"] == {"subnet": "192.168.1.0/24", "gateway": "192.168.1.1"}
    assert gw["device_type_guess"] == "router"


@pytest.mark.parametrize("bad", [
    [], {"devices": "x"}, {"devices": [1]}, {"devices": [{"ip": "evil"}]},
    {"devices": [{"ip": "10.0.0.1", "open_ports": [{"port": "80", "protocol": "tcp"}]}]},
    {"devices": [{"ip": "10.0.0.1", "open_ports": [{"port": 70000, "protocol": "tcp"}]}]},
    {"devices": [{"ip": "10.0.0.1", "open_ports": [{"port": 80, "protocol": "icmp"}]}]},
    {"devices": [{"ip": "10.0.0.1", "vendor": {"x": 1}}]},
])
def test_hostile_contract_payload_rejected(bad):
    with pytest.raises(contract.ContractError):
        contract.hosts_from_raw(bad)


# ------------------------------------------------------------------ „Dovedește!"
def _xml(ip, port, state="open", service="http", title=None):
    script = f'<script id="http-title" output="{title}"/>' if title else ""
    return (f'<?xml version="1.0"?><nmaprun><host><status state="up"/><address addr="{ip}" addrtype="ipv4"/>'
            f'<ports><port protocol="tcp" portid="{port}"><state state="{state}"/><service name="{service}"/>'
            f'{script}</port></ports></host></nmaprun>').encode()


F = Finding(ip="172.20.10.5", port=8080, protocol="tcp", code="HTTP_ADMIN_CLEARTEXT", severity="medium",
            points=10, evidence="x")
H = Host(ip="172.20.10.5", vendor="Raspberry Pi", hostnames=["pi"])


def test_verify_resolved_and_still_open():
    assert verify.verify(F, H, ALLOW, runner=lambda c: _xml("172.20.10.5", 8080, "closed")).status == "resolved"
    still = verify.verify(F, H, ALLOW, runner=lambda c: _xml("172.20.10.5", 8080, title="Admin Login"))
    assert still.status == "still_open" and "Încă" in still.message("ro")


def test_verify_guardrail_udp_unknown():
    assert verify.verify(Finding("8.8.8.8", 80, "tcp", "X", "medium", 10, ""), H, ALLOW,
                         runner=lambda c: b"").status == "refused"
    assert verify.verify(Finding("172.20.10.1", 1900, "udp", "UPNP_EXPOSED", "medium", 10, ""), H,
                         ALLOW).status == "needs_root"
    assert verify.verify(Finding("172.20.10.9", None, None, "UNKNOWN_DEVICE", "low", 5, ""), H,
                         ALLOW).status == "unsupported"
    cmd = verify.build_command("172.20.10.5", 8080, udp=False)
    assert "-sT" in cmd and "sudo" not in cmd


# ------------------------------------------------------------------ „Paznic"
ARP = """? (172.20.10.1) at 2a:3b:4c:5d:6e:7f on en0 ifscope [ethernet]
? (172.20.10.4) at (incomplete) on en0 ifscope [ethernet]
? (172.20.10.5) at b8:27:eb:1:2:3 on en0 ifscope [ethernet]
? (172.20.10.15) at ff:ff:ff:ff:ff:ff on en0 ifscope [ethernet]
172.20.10.6 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
  172.20.10.7          a4-83-e7-01-02-03     dynamic
10.0.0.9 dev eth0 lladdr 11:22:33:44:55:66 STALE"""


def test_parse_arp_all_platforms():
    assert watch.parse_arp(ARP, "172.20.10.0/28") == {
        "172.20.10.1": "2a:3b:4c:5d:6e:7f", "172.20.10.5": "b8:27:eb:01:02:03",
        "172.20.10.6": "aa:bb:cc:dd:ee:ff", "172.20.10.7": "a4:83:e7:01:02:03"}


def test_watch_events_and_private_state():
    obs = {"172.20.10.5": "b8:27:eb:01:02:03"}
    events, known = watch.compare({}, obs, {})
    assert [e.kind for e in events] == ["new_device"]
    telnet = [Port(protocol="tcp", portid=23, state="open", service="telnet")]
    events, known = watch.compare(known, obs, {"172.20.10.5": telnet})
    assert [e.kind for e in events] == ["new_port"] and events[0].risks == ["TELNET_OPEN:23"]
    assert watch.compare(known, obs, {"172.20.10.5": telnet})[0] == []
    watch.save_state("172.20.10.0/28", known)
    path = watch.home() / "watch_172.20.10.0_28.json"
    assert "b8:27:eb:01:02:03" not in path.read_text().lower()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert watch.load_state("172.20.10.0/28") == known


# ------------------------------------------------------------------ CLI commands
def test_cli_scan_refusals(capsys):
    from netcheck.net import netdetect as nd
    fake = nd.NetworkInfo("en0", "172.20.10.2", "255.255.255.240", "172.20.10.0/28", "172.20.10.1")
    import netcheck.net.netdetect as mod
    orig = mod.detect
    mod.detect = lambda: fake
    try:
        assert cli.main(["scan", "8.8.8.8", "--confirm"]) == 3
        assert cli.main(["scan", "192.168.1.0/24", "--confirm", "--lang", "en"]) == 3
        assert cli.main(["scan"]) == 3            # in scope but no --confirm
    finally:
        mod.detect = orig
    out = capsys.readouterr().out
    assert "REFUZAT" in out and "outside the allowlist" in out and "--confirm" in out


def test_cli_parse_and_detect_json(tmp_path, capsys, monkeypatch):
    assert cli.main(["parse", str(FIX), "--out", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("*.raw.json"))) == len(GOOD)
    capsys.readouterr()
    monkeypatch.setattr(netdetect, "detect", lambda: netdetect.NetworkInfo(
        "en0", "172.20.10.2", "255.255.255.240", "172.20.10.0/28", "172.20.10.1"))
    assert cli.main(["detect", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["network"] == {"subnet": "172.20.10.0/28", "gateway": "172.20.10.1"}


def test_cli_verify_needs_confirm():
    assert cli.main(["verify", str(FIX / "V2_smart_home.xml"), "192.168.1.40", "554"]) == 3


def test_cli_scan_end_to_end_with_fake_nmap(tmp_path, monkeypatch, capsys):
    """scan -> XML + §1 JSON (live subnet/gateway) -> saved in the local history (Tudor's module)."""
    import shutil
    monkeypatch.setattr(netdetect, "detect", lambda: netdetect.NetworkInfo(
        "en0", "192.168.1.50", "255.255.255.0", "192.168.1.0/24", "192.168.1.1"))

    def fake_run_scan(target, out_dir):
        assert target == "192.168.1.0/24"
        dst = Path(out_dir) / "scan_test.xml"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(_with_real_nmap_header((FIX / "V2_smart_home.xml").read_bytes()))
        return dst

    monkeypatch.setattr(scanner, "run_scan", fake_run_scan)
    assert cli.main(["scan", "--confirm", "--out", str(tmp_path / "scans")]) == 0
    raw = json.loads((tmp_path / "scans" / "scan_test.raw.json").read_text())
    assert raw["network"] == {"subnet": "192.168.1.0/24", "gateway": "192.168.1.1"}
    out = capsys.readouterr().out
    assert "score 40/100" in out and "history #1" in out
    assert cli.main(["history", "list"]) == 0 and "scan_test.xml" in capsys.readouterr().out



# ------------------------------------------------------------------ live check 4 also works with no network
@pytest.mark.parametrize("target", ["8.8.8.8", "1.1.1.0/24", "100.64.1.1", "10.20.0.0/24"])
def test_scan_refuses_even_without_a_network(monkeypatch, capsys, target):
    from netcheck import cli

    def no_net():
        raise netdetect.NetworkDetectError("no active IPv4 network found")
    monkeypatch.setattr(netdetect, "detect", no_net)
    assert cli.main(["scan", target, "--confirm", "--lang", "en"]) == 3
    assert "REFUSED" in capsys.readouterr().out


# ------------------------------------------------------------------ Test Set day: an unreadable file with another extension
def test_all_files_gives_every_file_a_row(tmp_path, capsys):
    import shutil
    from netcheck import cli
    shutil.copy(FIX / "V1_home_basic.xml", tmp_path / "T1.xml")
    (tmp_path / "T9_broken.nmap").write_bytes(b"<nmaprun><host>")
    (tmp_path / ".hidden").write_text("x")
    assert cli.main(["analyze", str(tmp_path), "--out", str(tmp_path / "r1")]) == 0
    out = capsys.readouterr().out
    assert "T9_broken.nmap" in out and "--all-files" in out                 # warned, not silently skipped
    assert (tmp_path / "r1" / "scores.csv").read_text().count("\n") == 2
    assert cli.main(["analyze", str(tmp_path), "--out", str(tmp_path / "r2"), "--all-files"]) == 0
    rows = (tmp_path / "r2" / "scores.csv").read_text().splitlines()
    assert rows == ["file,network_score", "T1.xml,90", "T9_broken.nmap,ERROR"]
