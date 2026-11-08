"""„Păzește casa": the guard inside the app (netcheck.net.watch.Guard) and its API."""
import pytest

from netcheck.core.models import Port
from netcheck.net import guardrail, netdetect, watch

SUBNET = "172.20.10.0/28"
NET = netdetect.NetworkInfo("en0", "172.20.10.2", "255.255.255.240", SUBNET, "172.20.10.1")
ARP_BASE = "? (172.20.10.1) at 2a:3b:4c:5d:6e:7f on en0\n? (172.20.10.5) at b8:27:eb:01:02:03 on en0\n"
ARP_PHONE = ARP_BASE + "? (172.20.10.9) at 3a:11:22:33:44:55 on en0\n"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_HOME", str(tmp_path / "nc"))
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "h.sqlite"))
    yield tmp_path / "nc"


class Net:
    """Scripted network: what the ARP table and the port check show on each look."""
    def __init__(self):
        self.arp, self.ports, self.net, self.looked = ARP_BASE, {}, NET, 0

    def guard(self, **kw):
        def detect():
            if self.net is None:
                raise netdetect.NetworkDetectError("offline")
            return self.net
        def discover(subnet):
            self.looked += 1
        return watch.Guard(interval=3600, detect=detect, discover_fn=discover, arp_fn=lambda: self.arp,
                           ports_fn=lambda ips: {ip: self.ports.get(ip, []) for ip in ips}, **kw)


def _start(g):
    g.on, g.subnet, g.my_ip, g.state = True, SUBNET, NET.ip, "learning"     # start() without the thread


def test_first_look_learns_quietly_then_a_new_device_is_told():
    n = Net(); g = n.guard(); _start(g)
    g.check_once()
    st = g.status()
    assert st["state"] == "watching" and st["known"] == 2 and st["events"] == []
    n.arp = ARP_PHONE
    n.ports = {"172.20.10.9": [Port("tcp", 23, "open", "telnet")]}
    g.check_once()
    ev = g.status()["events"][0]
    assert ev["kind"] == "new_device" and ev["ip"] == "172.20.10.9" and ev["private_mac"] is True
    assert ev["risks"] == ["TELNET_OPEN"] and ev["checking"] is False and ev["status"] == "new"
    assert ev["mac"] == "XX:XX:XX:XX:44:55"                         # masked (NFR-02)
    g.check_once()
    assert len(g.status()["events"]) == 1                            # told once


def test_new_open_door_on_a_known_device():
    n = Net(); g = n.guard(); _start(g)
    g.check_once()
    n.ports = {"172.20.10.5": [Port("tcp", 5900, "open", "vnc")]}
    g.check_once()
    ev = g.status()["events"][0]
    assert ev["kind"] == "new_port" and ev["ip"] == "172.20.10.5" and ev["risks"] == ["VNC_EXPOSED"]


def test_answer_is_remembered_and_saved_without_the_mac(home):
    n = Net(); g = n.guard(); _start(g)
    g.check_once(); n.arp = ARP_PHONE; g.check_once()
    ev = g.status()["events"][0]
    assert g.ack(ev["id"], mine=True) and g.status()["events"][0]["status"] == "mine"
    saved = (home / "watch_172.20.10.0_28.json").read_text()
    assert '"mine": true' in saved and "3a:11:22" not in saved.lower()
    assert not g.ack("nope", mine=False)


def test_stops_on_another_network_and_never_looks_at_it():
    n = Net(); g = n.guard(); _start(g)
    n.net = None                                     # Wi-Fi reconnecting: a pause
    g.check_once()
    assert g.status()["state"] == "paused" and g.status()["on"] is True and n.looked == 0
    n.net = netdetect.NetworkInfo("en0", "10.240.1.5", "255.255.0.0", "10.240.0.0/16", "10.240.0.3")
    g.check_once()                                   # another network: the consent was for the old one
    st = g.status()
    assert st["on"] is False and st["state"] == "moved" and n.looked == 0


def test_waits_while_a_full_check_runs():
    n = Net(); g = n.guard(busy=lambda: True); _start(g)
    g.check_once()
    assert n.looked == 0


def test_refuses_to_guard_a_public_or_too_big_network():
    g = Net().guard()
    for bad in ("8.8.8.0/28", "10.240.0.0/16"):
        with pytest.raises(guardrail.ScopeError):
            g.start(bad, None)
    assert g.status()["on"] is False


def test_forget_removes_everything_the_guard_kept(home):
    n = Net(); g = n.guard(); _start(g)
    g.check_once()
    assert list(home.glob("watch_*"))
    g.forget()
    assert not list(home.glob("watch_*")) and g.status() ["known"] == 0 and g.status()["on"] is False


def test_mac_vendor_from_nmaps_list(monkeypatch):
    monkeypatch.setattr(watch, "_OUI", {"B827EB": "Raspberry Pi Foundation"})
    assert watch.mac_vendor("b8:27:eb:01:02:03") == "Raspberry Pi Foundation"
    assert watch.mac_vendor("3a:11:22:33:44:55") is None             # private (random) address


# ------------------------------------------------------------------ API
@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient
    from netcheck.web import agent, api_v1
    from netcheck.web.app import app
    n = Net()
    g = n.guard()
    monkeypatch.setattr(api_v1, "guard", g)
    monkeypatch.setattr(agent, "network_info", lambda: {"ok": True, "subnet": SUBNET, "ip": NET.ip, "gateway": NET.gateway, "wifi": "RSH-PingFloyd"})
    c = TestClient(app)
    c.get("/")
    yield c, g, n
    g.stop()


def test_api_needs_consent_then_guards_and_stops(client):
    c, g, n = client
    assert c.get("/api/v1/guard").json()["on"] is False
    assert c.post("/api/v1/guard", json={"on": True}).status_code == 400
    r = c.post("/api/v1/guard", json={"on": True, "confirm": True})
    assert r.status_code == 200 and r.json()["on"] is True and r.json()["subnet"] == SUBNET
    assert c.post("/api/v1/guard", json={"on": False}).json()["on"] is False


def test_api_refuses_a_network_that_is_not_a_home_network(client, monkeypatch):
    c, g, n = client
    from netcheck.web import agent
    monkeypatch.setattr(agent, "network_info", lambda: {"ok": False, "code": "refused", "subnet": "10.240.0.0/16"})
    r = c.post("/api/v1/guard?lang=en", json={"on": True, "confirm": True})
    assert r.status_code == 403 and "cannot be guarded" in r.json()["error"]["message"]


def test_api_ack_and_delete_history_forgets_the_guard(client, home):
    c, g, n = client
    _start(g); g.check_once(); n.arp = ARP_PHONE; g.check_once()
    ev = c.get("/api/v1/guard").json()["events"][0]
    assert c.post("/api/v1/guard/ack", json={"id": ev["id"], "mine": False}).json()["ok"] is True
    assert c.get("/api/v1/guard").json()["events"][0]["status"] == "stranger"
    c.delete("/api/v1/history")
    assert c.get("/api/v1/guard").json()["events"] == [] and not list(home.glob("watch_*"))


def test_learning_does_not_wait_for_the_door_check():
    n = Net()
    seen = {}

    def slow_ports(ips):
        seen.update(g.status())                    # what the page sees while the doors are being checked
        return {ip: n.ports.get(ip, []) for ip in ips}
    g = watch.Guard(interval=3600, detect=lambda: NET, discover_fn=lambda s: None, arp_fn=lambda: n.arp, ports_fn=slow_ports)
    _start(g)
    g.check_once()
    assert seen["state"] == "watching" and seen["phase"] == "doors" and seen["known"] == 2 and seen["seen"] == 2
    assert g.status()["phase"] is None


def test_a_device_whose_doors_could_not_be_checked_gives_no_false_alerts():
    n = Net(); g = n.guard(); _start(g)
    g.ports_fn = None
    g._ports = lambda ips: {}                       # door check timed out: nobody answered
    g.check_once()
    g._ports = lambda ips: {"172.20.10.5": [Port("tcp", 80, "open", "http")]}
    g.check_once()
    assert g.status()["events"] == []               # first look at its doors, not a "new door"


def test_an_error_is_shown_with_its_reason():
    import threading
    import time

    def boom(subnet):
        raise OSError("nmap crashed")
    g = watch.Guard(interval=3600, detect=lambda: NET, discover_fn=boom, arp_fn=lambda: "", ports_fn=lambda ips: {})
    _start(g)
    t = threading.Thread(target=g._loop, daemon=True)
    t.start()
    for _ in range(100):                            # the first look fails at once; wait for it (max 2 s)
        if g.status()["state"] == "error":
            break
        time.sleep(0.02)
    st = g.status()
    g._stop.set(); t.join(1)
    assert st["state"] == "error" and "nmap crashed" in st["error"]


def test_devices_nmap_saw_count_even_when_the_system_arp_table_is_empty():
    xml = (b'<nmaprun><host><status state="up"/><address addr="172.20.10.1" addrtype="ipv4"/>'
           b'<address addr="2A:3B:4C:5D:6E:7F" addrtype="mac"/></host>'
           b'<host><status state="up"/><address addr="172.20.10.7" addrtype="ipv4"/>'
           b'<address addr="A4:83:E7:01:02:03" addrtype="mac" vendor="Apple"/></host>'
           b'<host><status state="up"/><address addr="172.20.10.2" addrtype="ipv4"/></host>'           # this computer: no MAC
           b'<host><status state="up"/><address addr="8.8.8.8" addrtype="ipv4"/>'
           b'<address addr="11:22:33:44:55:66" addrtype="mac"/></host></nmaprun>')
    assert watch.macs_from_xml(xml, SUBNET) == {"172.20.10.1": "2a:3b:4c:5d:6e:7f", "172.20.10.7": "a4:83:e7:01:02:03"}
    n = Net(); n.arp = ""                           # Windows: nmap's own ARP does not fill the system table
    g = watch.Guard(interval=3600, detect=lambda: NET, discover_fn=lambda s: watch.macs_from_xml(xml, s),
                    arp_fn=lambda: "", ports_fn=lambda ips: {})
    _start(g); g.check_once()
    assert g.status()["known"] == 2


def test_a_look_that_ends_after_turning_off_keeps_nothing():
    n = Net()
    def ports(ips):
        g.stop()                                    # the user turns it off while the doors are checked
        return {}
    g = watch.Guard(interval=3600, detect=lambda: NET, discover_fn=lambda s: None, arp_fn=lambda: ARP_PHONE, ports_fn=ports)
    _start(g); g.known = {"x": {"ip": "172.20.10.1", "ports": []}}
    g.check_once()
    st = g.status()
    assert st["on"] is False and st["known"] == 1 and st["state"] == "off"     # the late result is not saved
