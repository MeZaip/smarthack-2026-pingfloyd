"""The SafeHouse UI (ui/) served by the local agent with live data: the page, its data, uploads, delete."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "tests" / "fixtures" / "lab"
SYN = ROOT / "tests" / "fixtures" / "synthetic"
FULL_MAC = re.compile(r"\b(?:[0-9A-F]{2}:){5}[0-9A-F]{2}\b", re.I)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "history.sqlite"))
    monkeypatch.setenv("NETCHECK_LLM_PROVIDER", "none")
    from netcheck.web import app as web
    web._cache.clear()
    monkeypatch.setattr(web, "this_ip", lambda: "172.20.10.10")
    yield
    web._cache.clear()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    c = TestClient(app)
    c.get("/")          # the page sets the session cookie
    return c


def _data(client) -> dict:
    js = client.get("/data.js").text
    assert js.startswith("window.NETCHECK_DATA = ")
    return json.loads(js[len("window.NETCHECK_DATA = "):].rstrip().rstrip(";"))


def _upload(client, *paths, name=None):
    files = [("files", (name or p.name, p.read_bytes(), "text/xml")) for p in paths]
    return client.post("/api/v1/upload", files=files)


def test_root_is_the_safehouse_page_and_sets_the_session_cookie():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    r = TestClient(app).get("/")
    assert r.status_code == 200 and "<title>SafeHouse</title>" in r.text
    assert "nc_session" in r.headers["set-cookie"]
    for f in ("app.js", "styles.css", "device3d.js", "safehouse3d.js", "vendor/three.min.js"):
        assert TestClient(app).get("/" + f).status_code == 200, f


def test_only_the_ui_files_are_served(client):
    for bad in ("/index.py", "/README.md", "/..%2fnetcheck%2fweb%2fapp.py", "/vendor/../../CLAUDE.md"):
        assert client.get(bad).status_code == 404, bad


def test_empty_history_gives_live_data_without_scans(client):
    d = _data(client)
    assert d["live"] is True and d["scans"] == [] and d["history"]["changes"] is None
    assert set(d["simple"]) == set(d["texts"]) and "deviceLabels" in d


def test_lab_scans_newest_first_with_changes_and_masked_macs(client):
    r = _upload(client, LAB / "lab_01_before.xml", LAB / "lab_02_between.xml", LAB / "lab_03_final.xml")
    assert r.status_code == 200 and len(r.json()["saved"]) == 3 and r.json()["errors"] == []
    d = _data(client)
    assert [s["score"] for s in d["scans"]] == [80, 30, 0]            # newest first
    assert d["scans"][-1]["changes"] is None                          # the first one has nothing to compare with
    assert d["scans"][0]["changes"]["score_change"] == 50
    assert [r["network_score"] for r in d["history"]["trend"]] == [0, 30, 80]
    me = [x for s in d["scans"] for x in s["devices"] if x["me"]]
    assert me and {x["ip"] for x in me} == {"172.20.10.10"}          # "this computer"
    body = client.get("/data.js").text
    assert not FULL_MAC.search(body.replace(":XX:XX:XX", "")), "full MAC address in the page data"
    assert "</script" not in body.lower()
    # same data as JSON for the page to refresh itself after a check
    assert client.get("/api/v1/ui-data").json()["scans"][0]["scan_id"] == d["scans"][0]["scan_id"]


def test_broken_upload_is_kept_as_error_and_exported_with_ERROR(client, tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_EXPORTS", str(tmp_path / "exports"))
    j = _upload(client, SYN / "V7_broken.xml").json()
    assert j["saved"] == [] and j["errors"][0]["file"] == "V7_broken.xml" and j["errors"][0]["scan_id"] and j["message"]
    d = _data(client)
    assert [(s["file"], bool(s.get("error"))) for s in d["scans"]] == [("V7_broken.xml", True)]
    assert d["history"]["trend"] == [] and d["history"]["all"][0]["error"]           # never compared or analysed
    assert client.get("/api/scans").json() == []                                     # not in the §2 API either
    assert _upload(client, SYN / "V7_broken.xml").json()["errors"][0]["scan_id"] == j["errors"][0]["scan_id"]  # once


def test_export_of_saved_files_matches_the_expected_answers(client, tmp_path, monkeypatch):
    """Upload the whole validation folder (broken file included), export the saved files: identical to expected."""
    monkeypatch.setenv("NETCHECK_EXPORTS", str(tmp_path / "exports"))
    _upload(client, *sorted(SYN.glob("*.xml"), reverse=True))
    got = _zip(client.post("/api/v1/export/history"))
    assert got["scores.csv"] == (SYN / "expected_scores.csv").read_text(encoding="utf-8")
    assert got["findings.csv"] == (SYN / "expected_findings.csv").read_text(encoding="utf-8")


def test_upload_and_delete_need_the_session_cookie():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    fresh = TestClient(app)                                           # never loaded a page: no cookie
    r = fresh.post("/api/v1/upload", files=[("files", ("a.xml", (SYN / "V1_home_basic.xml").read_bytes(), "text/xml"))])
    assert r.status_code == 403
    assert fresh.delete("/api/v1/history").status_code == 403


def test_delete_history_empties_the_page(client):
    _upload(client, SYN / "V6a_before.xml", SYN / "V6b_after.xml")
    assert len(_data(client)["scans"]) == 2
    assert client.delete("/api/v1/history").json() == {"deleted": True}
    assert _data(client)["scans"] == []


def test_hostile_text_stays_data(client):
    evil = (b'<?xml version="1.0"?><nmaprun><host><status state="up"/><address addr="192.168.1.9" addrtype="ipv4"/>'
            b'<hostnames><hostname name="&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;"/></hostnames>'
            b'<ports><port protocol="tcp" portid="23"><state state="open"/><service name="telnet"/></port></ports>'
            b'</host></nmaprun>')
    client.post("/api/v1/upload", files=[("files", ("evil.xml", evil, "text/xml"))])
    body = client.get("/data.js").text
    assert "</script" not in body.lower()
    assert _data(client)["scans"][0]["devices"][0]["hostname"].startswith("</script>")   # kept as text


def test_every_api_path_the_page_calls_exists():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    from netcheck.web.api_v1 import router
    routes = {r.path for r in router.routes}
    used = set(re.findall(r'"(/api/v1/[a-z-]+)', js))
    assert used, "the page should call the local agent"
    for path in used:
        assert any(r == path or r.startswith(path + "/") for r in routes), path


# ------------------------------------------------------------------ "Export CSV" (FR-15) from the page
def _zip(resp) -> dict:
    import io
    import zipfile
    assert resp.status_code == 200 and resp.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        return {n: z.read(n).decode("utf-8") for n in z.namelist()}


def test_export_of_a_folder_is_identical_to_the_cli(client, tmp_path, monkeypatch):
    from netcheck.core.analysis import analyze_folder, write_results
    monkeypatch.setenv("NETCHECK_EXPORTS", str(tmp_path / "exports"))
    files = sorted(SYN.glob("*.xml"), reverse=True)                     # any order in, sorted by name out
    r = client.post("/api/v1/export", files=[("files", (p.name, p.read_bytes(), "text/xml")) for p in files])
    got = _zip(r)
    cli_f, cli_s = write_results(analyze_folder(SYN), tmp_path / "cli")
    assert got["findings.csv"] == cli_f.read_text(encoding="utf-8")
    assert got["scores.csv"] == cli_s.read_text(encoding="utf-8")
    assert "V7_broken.xml,ERROR" in got["scores.csv"]
    assert r.headers["x-safehouse-files"] == "8" and r.headers["x-safehouse-errors"] == "1"
    saved = list((tmp_path / "exports").glob("export_*/scores.csv"))
    assert len(saved) == 1 and saved[0].read_text(encoding="utf-8") == got["scores.csv"]
    assert _data(client)["scans"] == []                                  # exporting saves nothing to the history


def test_export_matches_the_expected_answers(client, tmp_path, monkeypatch):
    import csv
    import io
    monkeypatch.setenv("NETCHECK_EXPORTS", str(tmp_path / "exports"))
    files = [p for p in SYN.glob("*.xml")]
    got = _zip(client.post("/api/v1/export", files=[("files", (p.name, p.read_bytes(), "text/xml")) for p in files]))
    rows = lambda text: {tuple(r) for r in list(csv.reader(io.StringIO(text)))[1:]}   # noqa: E731
    assert rows(got["findings.csv"]) == rows((SYN / "expected_findings.csv").read_text(encoding="utf-8"))
    assert rows(got["scores.csv"]) == rows((SYN / "expected_scores.csv").read_text(encoding="utf-8"))


def test_export_of_saved_scans(client, tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_EXPORTS", str(tmp_path / "exports"))
    assert client.post("/api/v1/export/history").status_code == 404           # nothing saved yet
    _upload(client, LAB / "lab_01_before.xml", LAB / "lab_03_final.xml")
    got = _zip(client.post("/api/v1/export/history"))
    assert got["scores.csv"].splitlines() == ["file,network_score", "lab_01_before.xml,0", "lab_03_final.xml,80"]


def test_export_needs_the_session_cookie():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    fresh = TestClient(app)
    p = SYN / "V1_home_basic.xml"
    assert fresh.post("/api/v1/export", files=[("files", (p.name, p.read_bytes(), "text/xml"))]).status_code == 403


def test_scans_keep_the_order_they_were_saved_in(client, tmp_path, monkeypatch):
    """By index, not by the time inside the file: V6b (taken later) uploaded first stays first."""
    monkeypatch.setenv("NETCHECK_EXPORTS", str(tmp_path / "exports"))
    _upload(client, SYN / "V6b_after.xml")
    _upload(client, SYN / "V1_home_basic.xml")
    _upload(client, SYN / "V6a_before.xml")
    d = _data(client)
    assert [r["file"] for r in d["history"]["trend"]] == ["V6b_after.xml", "V1_home_basic.xml", "V6a_before.xml"]
    assert [s["file"] for s in d["scans"]] == ["V6a_before.xml", "V1_home_basic.xml", "V6b_after.xml"]   # newest first
    assert d["scans"][0]["changes"]["before_file"] == "V1_home_basic.xml"                            # the one saved before
    got = _zip(client.post("/api/v1/export/history"))
    assert [ln.split(",")[0] for ln in got["scores.csv"].splitlines()[1:]] == \
        ["V1_home_basic.xml", "V6a_before.xml", "V6b_after.xml"]                                   # like expected_scores.csv


def test_test_set_workflow_import_all_then_export_after_a_restart(client, tmp_path, monkeypatch):
    """The Test Set day: empty history, import a whole folder (more than 20 files, any order, one broken),
    restart the app (no in-memory cache), export the saved checks -> identical to the CLI on that folder."""
    import random
    import shutil
    from netcheck.core.analysis import analyze_folder, write_results
    from netcheck.web import app as web
    monkeypatch.setenv("NETCHECK_EXPORTS", str(tmp_path / "exports"))
    folder = tmp_path / "testset"
    folder.mkdir()
    sources = sorted(SYN.glob("*.xml")) + sorted(LAB.glob("*.xml"))
    for i in range(3):                                         # 33 files, names like a real Test Set
        for p in sources:
            shutil.copy(p, folder / f"T{i}_{p.name}")
    files = list(folder.glob("*.xml"))
    random.Random(7).shuffle(files)
    r = _upload(client, *files)
    assert r.status_code == 200 and len(r.json()["saved"]) + len(r.json()["errors"]) == len(files) == 33
    web._cache.clear()                                         # as after closing and reopening the app
    got = _zip(client.post("/api/v1/export/history"))
    cli_f, cli_s = write_results(analyze_folder(folder), tmp_path / "cli")
    assert got["scores.csv"] == cli_s.read_text(encoding="utf-8")
    assert got["findings.csv"] == cli_f.read_text(encoding="utf-8")
    assert got["scores.csv"].count(",ERROR") == 3
