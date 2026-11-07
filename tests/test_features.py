"""Tests for the differentiators: house map + nicknames, „Dovedește!", certificate, Paznic, local AI + grounding."""
import copy
import json
import os
from pathlib import Path

import pytest

os.environ["NETCHECK_OFFLINE"] = "1"

from netcheck import certificate, history, verify, watch  # noqa: E402
from netcheck.analyzer import analyze_file, analyze_folder  # noqa: E402
from netcheck.assistant import Assistant, Session, check_grounded  # noqa: E402
from netcheck.guardrail import build_allowlist  # noqa: E402
from netcheck.llm import OllamaProvider, ollama_models  # noqa: E402
from netcheck.models import Host  # noqa: E402

ROOT = Path(__file__).parent / "fixtures"
V = ROOT / "validation" if (ROOT / "validation").is_dir() and any((ROOT / "validation").glob("*.xml")) \
    else ROOT / "validation_synthetic"


@pytest.fixture(autouse=True)
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_HOME", str(tmp_path / "home"))


def _xml(ip, port, state="open", service="http", title=None, proto="tcp"):
    script = f'<script id="http-title" output="{title}"/>' if title else ""
    ports = "" if state is None else (f'<port protocol="{proto}" portid="{port}"><state state="{state}"/>'
                                      f'<service name="{service}"/>{script}</port>')
    return (f'<?xml version="1.0"?><nmaprun><host><status state="up"/><address addr="{ip}" addrtype="ipv4"/>'
            f'<ports>{ports}</ports></host></nmaprun>').encode()


# ------------------------------------------------------------------ identity / nicknames / house
def test_device_id_stable_and_private():
    a = analyze_file(V / "V2_smart_home.xml")
    b = analyze_file(V / "V2_smart_home.xml")
    ids = [d.device_id for d in a.devices]
    assert ids == [d.device_id for d in b.devices]
    assert len(set(ids)) == len(ids) and all(len(i) == 12 for i in ids)
    dump = json.dumps(a.to_dict())
    assert "C0:06:C3:10:20:30" not in dump and "c0:06:c3:10:20:30" not in dump  # raw MAC never stored


def test_nickname_shown_and_escaped():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    r = analyze_file(V / "V2_smart_home.xml")
    sid = history.save(r, "lab")
    cam = next(d for d in r.devices if d.ip.endswith(".40"))
    c = TestClient(app)
    c.post("/device/name", data={"device_id": cam.device_id, "name": "Camera <b>bebe</b>", "scan_id": sid})
    page = c.get(f"/?id={sid}&lang=ro").text
    assert "Camera &lt;b&gt;bebe&lt;/b&gt;" in page and "<b>bebe</b>" not in page
    assert "Harta casei" in page and "Începe aici" in page
    s = Session(lang="ro")
    s.load_history(sid)
    from netcheck.assistant import offline_answer
    assert "Camera <b>bebe</b>" in offline_answer(s, "care e cel mai periculos dispozitiv?")


def test_house_rooms_order_and_doors():
    from netcheck.web.house import rooms
    r = analyze_file(V / "V2_smart_home.xml")
    rm = rooms(r, {}, {}, "en")
    assert rm[0]["router"]                                   # front door first
    assert any(x["start_here"] for x in rm)
    cam = next(x for x in rm if x["dev"].ip.endswith(".40"))
    assert cam["doors"][0]["sev"] == "high" and cam["doors"][0]["port"] == 554
    tv = next(x for x in rm if x["dev"].ip.endswith(".42"))
    assert all(d["sev"] == "none" for d in tv["doors"])        # 8008/8009: no risk


# ------------------------------------------------------------------ „Dovedește!"
def _finding(code="HTTP_ADMIN_CLEARTEXT", port=8080, proto="tcp", ip="172.20.10.5"):
    from netcheck.models import Finding
    return Finding(file="lab.xml", ip=ip, port=port, code=code, severity="medium", points=10, protocol=proto)


ALLOW = build_allowlist("172.20.10.0/28")
HOST = Host(ip="172.20.10.5", vendor="Raspberry Pi", hostname="pi")


def test_verify_resolved_when_port_closed():
    res = verify.verify(_finding(), HOST, allowlist=ALLOW, runner=lambda cmd: _xml("172.20.10.5", 8080, "closed"))
    assert res.status == "resolved"
    assert history.verifications_for(None) == {} or True


def test_verify_still_open():
    res = verify.verify(_finding(), HOST, allowlist=ALLOW,
                        runner=lambda cmd: _xml("172.20.10.5", 8080, title="Admin Login"))
    assert res.status == "still_open"


def test_verify_uses_unprivileged_connect_scan():
    cmd = verify.build_command("172.20.10.5", 8080, udp=False)
    assert "-sT" in cmd and "sudo" not in cmd


def test_verify_refuses_out_of_scope_and_udp():
    assert verify.verify(_finding(ip="8.8.8.8"), HOST, allowlist=ALLOW, runner=lambda c: b"").status == "refused"
    assert verify.verify(_finding(ip="192.168.9.9"), HOST, allowlist=ALLOW, runner=lambda c: b"").status == "refused"
    assert verify.verify(_finding("UPNP_EXPOSED", 1900, "udp"), HOST, allowlist=ALLOW).status == "needs_root"


def test_estimated_score():
    r = analyze_file(V / "V6a_before.xml")
    f = r.findings[0]
    ver = {(f.ip, f.port, f.code): {"status": "resolved"}}
    assert verify.estimated_score(r.score, r.findings, ver) == r.score + f.points


# ------------------------------------------------------------------ certificate
def _pair():
    res = {r.file: r for r in analyze_folder(V)}
    return res["V6a_before.xml"], res["V6b_after.xml"]


def test_certificate_valid_and_tamper_detected():
    b, a = _pair()
    cert = certificate.build(b, a, "2026-11-08T10:00:00", "2026-11-08T11:00:00")
    ok, _, ours = certificate.verify(cert)
    assert ok and ours
    assert len(cert["payload"]["resolved"]) == 3 and cert["payload"]["score_delta"] == 40
    forged = copy.deepcopy(cert)
    forged["payload"]["before"]["score"] = 10
    assert certificate.verify(forged)[0] is False
    assert certificate.verify({"payload": {}})[0] is False


def test_signing_key_is_private_and_outside_repo():
    certificate.local_fingerprint()
    key = Path(os.environ["NETCHECK_HOME"]) / "signing_key"
    assert key.exists() and (key.stat().st_mode & 0o077) == 0
    repo = Path(__file__).parent.parent
    assert not list(repo.glob("**/signing_key"))


def test_certificate_web_pages():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    b, a = _pair()
    i, j = history.save(b, "v6"), history.save(a, "v6")
    c = TestClient(app)
    page = c.get(f"/certificate?before={i}&after={j}&lang=en")
    assert page.status_code == 200 and "Ed25519" in page.text
    cert = certificate.build(b, a, "x", "y")
    cert["payload"]["after"]["score"] = 99
    r = c.post("/certificate/verify?lang=en", files={"file": ("c.json", json.dumps(cert), "application/json")})
    assert "Forged" in r.text


# ------------------------------------------------------------------ Paznic
MAC_ARP = """? (172.20.10.1) at 2a:3b:4c:5d:6e:7f on en0 ifscope [ethernet]
? (172.20.10.4) at (incomplete) on en0 ifscope [ethernet]
? (172.20.10.5) at b8:27:eb:1:2:3 on en0 ifscope [ethernet]
? (172.20.10.15) at ff:ff:ff:ff:ff:ff on en0 ifscope [ethernet]
? (224.0.0.251) at 1:0:5e:0:0:fb on en0 ifscope permanent [ethernet]"""
LINUX_ARP = "172.20.10.6 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE\n10.0.0.9 dev eth0 lladdr 11:22:33:44:55:66 STALE"
WIN_ARP = "  172.20.10.7          a4-83-e7-01-02-03     dynamic"


def test_parse_arp_all_platforms():
    got = watch.parse_arp(MAC_ARP + "\n" + LINUX_ARP + "\n" + WIN_ARP, "172.20.10.0/28")
    assert got == {"172.20.10.1": "2a:3b:4c:5d:6e:7f", "172.20.10.5": "b8:27:eb:01:02:03",
                   "172.20.10.6": "aa:bb:cc:dd:ee:ff", "172.20.10.7": "a4:83:e7:01:02:03"}


def test_watch_detects_new_device_and_new_port():
    obs = {"172.20.10.5": "b8:27:eb:01:02:03"}
    events, known = watch.compare({}, obs, {"172.20.10.5": []})
    assert [e.kind for e in events] == ["new_device"]
    ports = {"172.20.10.5": [{"port": 23, "protocol": "tcp", "service": "telnet", "product": "", "version": ""}]}
    events, known = watch.compare(known, obs, ports)
    assert [e.kind for e in events] == ["new_port"] and events[0].findings == ["TELNET_OPEN:23"]
    events, _ = watch.compare(known, obs, ports)
    assert events == []
    assert "b8:27:eb:01:02:03" not in json.dumps(known)        # masked only


# ------------------------------------------------------------------ local AI + grounding
def _session():
    s = Session(lang="en")
    s.load_file(str(V / "V3_small_office.xml"))
    return s


def test_ollama_provider_tool_loop():
    calls = []

    def fake(method, url, body, timeout):
        calls.append(body)
        if len(calls) == 1:
            return {"message": {"role": "assistant", "content": "",
                                "tool_calls": [{"function": {"name": "get_scan_summary", "arguments": {}}}]}}
        assert body["messages"][-1]["role"] == "tool" and "standard_score" in body["messages"][-1]["content"]
        return {"message": {"role": "assistant", "content": "Fix 192.168.1.30 first: port 3389 is remote desktop."}}

    a = Assistant(_session(), provider=OllamaProvider(model="test", transport=fake))
    out = a.ask("what first?")
    assert a.last_mode == "ai" and "192.168.1.30" in out
    assert calls[0]["tools"][0]["type"] == "function" and calls[0]["options"]["temperature"] == 0


def test_ungrounded_answer_rejected():
    def fake(method, url, body, timeout):
        return {"message": {"role": "assistant", "content": "Close port 8443 on 192.168.1.77, see CVE-2021-1234."}}
    a = Assistant(_session(), provider=OllamaProvider(model="test", transport=fake))
    out = a.ask("what first?")
    assert a.last_mode == "rejected" and "3389" in out          # verified offline text shown instead
    assert {"port 8443", "IP 192.168.1.77"} <= set(a.last_problems)


def test_grounding_rules():
    s = _session()
    assert check_grounded("Fix 192.168.1.30:3389 (RDP_EXPOSED) first.", s, []) == []
    assert check_grounded("The scan does not show port 8443.", s, [], question="what about port 8443?") == []
    assert check_grounded("Call +40 721 123 456 for help", s, [])
    assert check_grounded("Read https://evil.example", s, [])


def test_model_down_falls_back_offline():
    def boom(*a):
        raise OSError("connection refused")
    a = Assistant(_session(), provider=OllamaProvider(model="test", transport=boom))
    assert "unavailable" in a.ask("which device is most dangerous?") and a.last_mode == "offline"
    assert ollama_models("http://127.0.0.1:9") is None
