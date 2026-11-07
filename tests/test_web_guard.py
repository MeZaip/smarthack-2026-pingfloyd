"""„Paznic" from the web UI: baseline then alerts, catalogue risks, pause on other network,
yields to a full scan, consent/CSRF/local-only, 'delete my history' wipes its memory, MACs masked."""
import time

import pytest

from netcheck.core.models import Port
from netcheck.net import netdetect, watch

NET = netdetect.NetworkInfo(interface="wlan0", ip="172.20.10.2", netmask="255.255.255.240",
                            subnet="172.20.10.0/28", gateway="172.20.10.1")
OTHER = netdetect.NetworkInfo(interface="wlan0", ip="10.1.1.2", netmask="255.255.255.0",
                              subnet="10.1.1.0/24", gateway="10.1.1.1")


class Lab:
    """Fake network: what ARP shows and which ports are open. Nothing touches the real network."""
    def __init__(self):
        self.net = NET
        self.arp = {"172.20.10.1": "2a:3b:4c:5d:6e:7f", "172.20.10.2": "aa:aa:aa:aa:aa:aa"}
        self.ports = {}
        self.discovered = 0

    def arp_text(self):
        return "\n".join(f"{ip} dev wlan0 lladdr {mac} REACHABLE" for ip, mac in self.arp.items())


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "history.sqlite"))
    monkeypatch.setenv("NETCHECK_LLM_PROVIDER", "none")
    monkeypatch.delenv("NETCHECK_ALLOWLIST", raising=False)
    lab = Lab()
    monkeypatch.setattr(netdetect, "detect", lambda: lab.net)
    monkeypatch.setattr(watch, "discover", lambda subnet: setattr(lab, "discovered", lab.discovered + 1))
    monkeypatch.setattr(watch, "read_arp_table", lab.arp_text)
    monkeypatch.setattr(watch, "quick_ports", lambda ips: {ip: lab.ports.get(ip, []) for ip in ips})
    monkeypatch.setattr(watch, "notify", lambda title, text: None)
    from netcheck.web import app as web, guard, livescan
    monkeypatch.setattr(web, "_is_local", lambda request: True)
    guard.reset()
    livescan.reset()
    yield lab
    guard.reset()
    livescan.reset()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    return TestClient(app)


def _state():
    from netcheck.web import guard
    st = guard.GuardState(running=True, subnet=NET.subnet)
    return guard, st


def test_first_cycle_is_a_baseline_then_new_device_and_risky_port_alert(lab):
    guard, st = _state()
    guard.run_cycle(NET, st)
    assert st.baseline and st.known == 1 and not st.events      # own laptop (.2) is not counted
    lab.arp["172.20.10.9"] = "b8:27:eb:01:02:03"
    guard.run_cycle(NET, st)
    assert [e.event.kind for e in st.events] == ["new_device"]
    lab.ports["172.20.10.9"] = [Port(protocol="tcp", portid=2323, state="open", service="telnet")]
    guard.run_cycle(NET, st)
    newest = st.events[0]
    assert newest.event.kind == "new_port" and newest.risky
    assert newest.event.risks == ["TELNET_OPEN:2323"]           # catalogue rule, by service not port
    title, text = newest.text("ro")
    assert "Ușă nouă" in title and "b8:27:eb" not in text.lower()


def test_pauses_on_another_network_and_yields_to_a_full_scan(lab):
    guard, st = _state()
    lab.net = OTHER
    guard.run_cycle(NET, st)
    assert st.status == "paused" and lab.discovered == 0
    lab.net = NET
    guard.set_busy_check(lambda: True)
    try:
        guard.run_cycle(NET, st)
        assert st.status == "skipped" and lab.discovered == 0
    finally:
        from netcheck.web import app as web
        guard.set_busy_check(web._scan_running)


def test_start_needs_consent_csrf_and_local_access(client, lab, monkeypatch):
    from netcheck.web import app as web, guard
    r = client.post("/guard/start?lang=en", data={"interval": 60, "csrf": web._CSRF})
    assert r.status_code == 400 and "explicit consent" in r.text and not guard.state().running
    r = client.post("/guard/start", data={"interval": 60, "confirm": "yes", "csrf": "forged"})
    assert r.status_code == 403 and not guard.state().running
    monkeypatch.setattr(web, "_is_local", lambda request: False)
    r = client.post("/guard/start", data={"interval": 60, "confirm": "yes", "csrf": web._CSRF})
    assert r.status_code == 403 and not guard.state().running


def test_start_and_stop_from_the_page(client, lab, monkeypatch):
    from netcheck.web import app as web, guard
    cycles = []
    monkeypatch.setattr(guard, "run_cycle", lambda net, st: cycles.append(net.subnet))
    r = client.post("/guard/start?lang=en", data={"interval": 60, "confirm": "yes", "csrf": web._CSRF},
                    follow_redirects=False)
    assert r.status_code == 303 and guard.state().running
    for _ in range(100):
        if cycles:
            break
        time.sleep(0.02)
    assert cycles == ["172.20.10.0/28"]
    assert "172.20.10.0/28" in client.get("/guard?lang=en").text
    client.post("/guard/stop", data={"csrf": web._CSRF})
    for _ in range(100):
        if not guard.state().running:
            break
        time.sleep(0.02)
    assert not guard.state().running


def test_delete_my_history_wipes_guard_memory(client, lab):
    guard, st = _state()
    guard.run_cycle(NET, st)
    assert watch.load_state(NET.subnet)
    client.post("/history/delete")
    assert watch.load_state(NET.subnet) == {}
    assert not (watch.home() / "watch_events.log").exists()


def test_guard_events_show_on_dashboard_and_guard_page(client, lab):
    from netcheck.web import guard
    st = guard.state()
    st.subnet, st.baseline = NET.subnet, True
    lab.arp["172.20.10.9"] = "b8:27:eb:01:02:03"
    guard.run_cycle(NET, st)
    page = client.get("/guard?lang=en").text
    assert "New device on your Wi-Fi" in page and "XX:XX:XX:XX:02:03" in page
    assert "b8:27:eb" not in page.lower()
    from pathlib import Path
    from netcheck import history
    from netcheck.core.analysis import analyze_file
    xml = sorted((Path(__file__).parent / "fixtures" / "synthetic").glob("*.xml"))[0]
    with history.open_history() as conn:
        history.save(conn, analyze_file(xml))
    home = client.get("/?lang=en").text
    assert "What the guard noticed" in home and "XX:XX:XX:XX:02:03" in home
