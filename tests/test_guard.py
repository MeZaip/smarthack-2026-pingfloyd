"""„Păzește casa": the guard inside the app (netcheck.net.watch.Guard) and its API.
It only watches WHO is on the network; open doors are the job of the full check."""
import threading
import time

import pytest

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
    """Scripted network: what the ARP table shows on each look."""
    def __init__(self):
        self.arp, self.net, self.looked = ARP_BASE, NET, 0

    def guard(self, **kw):
        def detect():
            if self.net is None:
                raise netdetect.NetworkDetectError("offline")
            return self.net

        def discover(subnet):
            self.looked += 1
        return watch.Guard(interval=3600, detect=detect, discover_fn=discover, arp_fn=lambda: self.arp, **kw)


def _start(g):
    g.on, g.subnet, g.my_ip, g.state, g.learned = True, SUBNET, NET.ip, "learning", False   # start() without the thread


def test_first_look_learns_quietly_then_a_new_device_is_told_at_once():
    n = Net(); g = n.guard(); _start(g)
    g.check_once()
    st = g.status()
    assert st["state"] == "watching" and st["known"] == 2 and st["events"] == []
    n.arp = ARP_PHONE
    g.check_once()
    ev = g.status()["events"][0]
    assert ev["kind"] == "new_device" and ev["ip"] == "172.20.10.9" and ev["private_mac"] is True and ev["status"] == "new"
    assert ev["mac"] == "XX:XX:XX:XX:44:55"                          # masked (NFR-02)
    assert "ports" not in ev and "risks" not in ev                   # only devices: doors are the full check's job
    g.check_once()
    assert len(g.status()["events"]) == 1                            # told once


def test_the_guard_never_runs_a_port_scan(monkeypatch):
    monkeypatch.setattr(watch, "quick_ports", lambda ips: pytest.fail("the guard must not scan ports"))
    n = Net(); g = n.guard(); _start(g)
    g.check_once(); n.arp = ARP_PHONE; g.check_once()
    assert g.status()["events"]


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
    assert n.looked == 0 and g.status()["phase"] == "waiting"


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
    assert not list(home.glob("watch_*")) and g.status()["known"] == 0 and g.status()["on"] is False


def test_mac_vendor_from_nmaps_list(monkeypatch):
    monkeypatch.setattr(watch, "_OUI", {"B827EB": "Raspberry Pi Foundation"})
    assert watch.mac_vendor("b8:27:eb:01:02:03") == "Raspberry Pi Foundation"
    assert watch.mac_vendor("3a:11:22:33:44:55") is None             # private (random) address


def test_an_error_is_shown_with_its_reason():
    def boom(subnet):
        raise OSError("nmap crashed")
    g = watch.Guard(interval=3600, detect=lambda: NET, discover_fn=boom, arp_fn=lambda: "")
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
    g = watch.Guard(interval=3600, detect=lambda: NET, discover_fn=lambda s: watch.macs_from_xml(xml, s), arp_fn=lambda: "")
    _start(g); g.check_once()                       # Windows: nmap's own ARP does not fill the system table
    assert g.status()["known"] == 2


def test_a_look_that_ends_after_turning_off_keeps_nothing():
    n = Net()

    def discover(subnet):
        g.stop()                                    # the user turns it off while the look runs
    g = watch.Guard(interval=3600, detect=lambda: NET, discover_fn=discover, arp_fn=lambda: ARP_PHONE)
    _start(g)
    g.check_once()
    st = g.status()
    assert st["on"] is False and st["state"] == "off" and st["known"] == 0


def test_lists_the_devices_and_can_forget_them(home):
    n = Net(); g = n.guard(); _start(g)
    g.check_once()
    devs = g.status()["devices"]
    assert [d["ip"] for d in devs] == ["172.20.10.1", "172.20.10.5"] and all(d["online"] for d in devs)
    assert all(d["mac"].startswith("XX:XX:XX:XX:") and d["mine"] is None for d in devs)
    n.arp = "? (172.20.10.1) at 2a:3b:4c:5d:6e:7f on en0\n"           # .5 left
    g.check_once()
    devs = {d["ip"]: d for d in g.status()["devices"]}
    assert devs["172.20.10.1"]["online"] and not devs["172.20.10.5"]["online"]
    dev5 = devs["172.20.10.5"]["id"]
    assert g.device(dev5, "mine") and {d["ip"]: d for d in g.status()["devices"]}["172.20.10.5"]["mine"] is True
    assert '"mine": true' in (home / "watch_172.20.10.0_28.json").read_text()
    assert not g.device("nope", "mine") and not g.device(dev5, "explode")
    assert g.device(dev5, "forget") and [d["ip"] for d in g.status()["devices"]] == ["172.20.10.1"]
    n.arp = ARP_BASE; g.check_once()                                    # forgotten and back: told as new
    assert g.status()["events"][0]["ip"] == "172.20.10.5"
    g.forget_network()
    st = g.status()
    assert st["known"] == 0 and st["devices"] == [] and st["state"] == "learning"
    assert not (home / "watch_172.20.10.0_28.json").exists()
    g.check_once()                                                      # "forget all": learns again quietly
    assert g.status()["events"] == [] and g.status()["known"] == 2


def test_forgetting_the_only_device_still_warns_when_it_comes_back(home):
    n = Net(); n.arp = "? (172.20.10.1) at 2a:3b:4c:5d:6e:7f on en0\n"
    g = n.guard(); _start(g)
    g.check_once()                                   # first look: learns the hotspot quietly
    did = g.status()["devices"][0]["id"]
    assert g.device(did, "forget") and g.status()["known"] == 0
    g.check_once()                                   # it is still there: told as a new device
    ev = g.status()["events"]
    assert len(ev) == 1 and ev[0]["ip"] == "172.20.10.1"
    g2 = n.guard(); g2.start(SUBNET, NET.ip); g2.stop()
    assert g2.learned is True                        # the network was looked at before, even if its list was empty


def test_faster_on_a_small_network():
    g = Net().guard(); g.interval = None
    g.subnet = "172.20.10.0/28"; assert g.interval == 8
    g.subnet = "192.168.1.0/24"; assert g.interval == 20


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


def test_api_ack_device_actions_and_delete_history(client, home):
    c, g, n = client
    _start(g); g.check_once(); n.arp = ARP_PHONE; g.check_once()
    ev = c.get("/api/v1/guard").json()["events"][0]
    assert c.post("/api/v1/guard/ack", json={"id": ev["id"], "mine": False}).json()["ok"] is True
    assert c.get("/api/v1/guard").json()["events"][0]["status"] == "stranger"
    did = c.get("/api/v1/guard").json()["devices"][0]["id"]
    assert c.post("/api/v1/guard/device", json={"id": did, "action": "hack"}).status_code == 422
    r = c.post("/api/v1/guard/device", json={"id": did, "action": "forget"})
    assert r.json()["ok"] is True and did not in [d["id"] for d in r.json()["devices"]]
    r = c.post("/api/v1/guard/forget")
    assert r.json()["known"] == 0
    c.delete("/api/v1/history")
    assert c.get("/api/v1/guard").json()["events"] == [] and not list(home.glob("watch_*"))
