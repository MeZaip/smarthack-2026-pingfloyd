"""Desktop app server: live data, one-click scan, phone sharing - and the security around them."""
import http.client
import json
import re
import shutil
import threading
import time
from pathlib import Path

import pytest

from netcheck.net import netdetect, scanner
from netcheck.web import server, uidata

SYN = Path(__file__).parent / "fixtures" / "synthetic"
NET = netdetect.NetworkInfo("en0", "127.0.0.1", "255.255.255.240", "192.168.1.0/28", "192.168.1.1")


def fake_scan(target, out_dir, mode):
    out = Path(out_dir) / "scan_20261107_120000.xml"
    shutil.copy(SYN / "V3_small_office.xml", out)
    return out


@pytest.fixture
def app(tmp_path, monkeypatch):
    a = server.App(tmp_path / "scans", str(tmp_path / "h.sqlite"), detect=lambda: NET, scan_runner=fake_scan)
    a.find_nmap = lambda: "/usr/bin/nmap"
    srv = server.start(a, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield a, srv.server_address[1]
    a.phone_off()
    srv.shutdown()
    srv.server_close()


def req(port, method, path, body=None, headers=None, host=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request(method, path, body=json.dumps(body) if isinstance(body, dict) else body,
              headers={"Host": host or f"127.0.0.1:{port}", **(headers or {})})
    r = c.getresponse()
    data = r.read()
    c.close()
    return r.status, data, r


def post(a, port, path, body):
    return req(port, "POST", path, body, {"Content-Type": "application/json", "X-Netcheck-Token": a.token})


def test_build_quick_command_needs_no_root(tmp_path):
    cmd = scanner.build_command("192.168.1.0/28", tmp_path / "x.xml", mode="quick")
    assert "-sT" in cmd and "-sS" not in cmd and "-sU" not in cmd and "--max-rate" in cmd
    assert scanner.build_command("192.168.1.0/28", tmp_path / "x.xml")[1:3] == ["-sS", "-sU"]   # CLI unchanged


def test_live_data_has_examples_and_no_full_mac(tmp_path):
    d = uidata.live_data(tmp_path / "none", str(tmp_path / "h.sqlite"))
    assert d["mode"] == "app" and d["own_scans"] == 0 and d["history_is_example"]
    js = uidata.to_js(d)
    assert not re.search(r"\b(?:[0-9A-F]{2}:){5}[0-9A-F]{2}\b", js.replace(":XX:XX:XX", ""), re.I)


def test_page_injects_config_and_needs_right_host(app):
    a, port = app
    status, body, _ = req(port, "GET", "/")
    assert status == 200 and b'<script src="config.js"></script>' in body
    status, body, _ = req(port, "GET", "/config.js")
    assert a.token.encode() in body
    assert req(port, "GET", "/data.js", host="evil.example")[0] == 403
    assert req(port, "GET", "/../netcheck/cli.py")[0] == 404


def test_post_needs_token_and_confirmation(app):
    a, port = app
    assert req(port, "POST", "/api/scan", {"confirm": True, "mode": "quick"}, {"Content-Type": "application/json"})[0] == 403
    assert post(a, port, "/api/scan", {"mode": "quick"})[0] == 400


def test_one_click_scan_then_data_shows_my_network(app):
    a, port = app
    status, body, _ = post(a, port, "/api/scan", {"confirm": True, "mode": "quick"})
    r = json.loads(body)
    assert status == 200 and r["started"] and r["target"] == "192.168.1.0/28"
    for _ in range(50):
        j = json.loads(req(port, "GET", f"/api/scan/status?job={r['job']}")[1])
        if j["state"] != "running":
            break
        time.sleep(0.05)
    assert j["state"] == "done" and j["score"] == 45
    js = req(port, "GET", "/data.js")[1].decode()
    assert "My network" in js and '"own_scans": 1' in js
    assert json.loads(post(a, port, "/api/history/delete", {"confirm": True})[1])["scans_removed"] == 1


def test_scan_refused_outside_private_range(app, monkeypatch):
    a, port = app
    a.detect = lambda: netdetect.NetworkInfo("en0", "8.8.8.8", "255.255.255.0", "8.8.8.0/24", "8.8.8.1")
    r = json.loads(post(a, port, "/api/scan", {"confirm": True, "mode": "quick"})[1])
    assert r["started"] is False and r["reason"] == "refused"


def test_phone_listener_is_read_only_and_needs_key(app):
    a, port = app
    phone = json.loads(post(a, port, "/api/phone", {"on": True})[1])["phone"]
    m = re.match(r"http://([\d.]+):(\d+)/\?k=(.+)$", phone["url"])
    host, pport, key = m.group(1), int(m.group(2)), m.group(3)
    assert req(pport, "GET", "/data.js", host=f"{host}:{pport}")[0] == 403              # no key
    status, _, resp = req(pport, "GET", f"/?k={key}", host=f"{host}:{pport}")
    assert status == 200 and "nck=" in resp.getheader("Set-Cookie")
    assert req(pport, "GET", "/config.js", headers={"Cookie": f"nck={key}"}, host=f"{host}:{pport}")[1].count(b'"token": null') == 1
    assert req(pport, "POST", "/api/scan", {"confirm": True}, {"Content-Type": "application/json",
               "X-Netcheck-Token": a.token}, host=f"{host}:{pport}")[0] == 403              # read-only
    assert req(pport, "GET", "/api/state", headers={"Cookie": f"nck={key}"}, host=f"{host}:{pport}")[0] == 404
    if server.qr_svg("x"):
        assert req(port, "GET", "/api/phone/qr.svg")[1].startswith(b"<svg")
    post(a, port, "/api/phone", {"on": False})
    with pytest.raises(OSError):
        req(pport, "GET", f"/?k={key}", host=f"{host}:{pport}")
