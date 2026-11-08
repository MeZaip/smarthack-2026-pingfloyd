"""JSON API on top of core/ and history: contract shapes (§2, §4), MAC masking, hostile input."""
import json
import re
from pathlib import Path

import pytest

from netcheck import history
from netcheck.core import contract
from netcheck.core.analysis import analyze_file
from netcheck.core.device import mask_mac
from netcheck.core.diff import compare

REPO = Path(__file__).parent.parent
SYN = Path(__file__).parent / "fixtures" / "validation"
GOOD = sorted(p for p in SYN.glob("*.xml") if "broken" not in p.name)

_BLOCKS = re.findall(r"```json\n(.*?)```", (REPO / "service_data_contracts.md").read_text(encoding="utf-8"), re.S)
_RAW, EVALUATED, _LLM_REQ, _LLM_RESP, DELTA = [json.loads(b) for b in _BLOCKS]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_DB", str(tmp_path / "history.sqlite"))
    monkeypatch.setenv("NETCHECK_LLM_PROVIDER", "none")      # never call a real gateway from tests
    from netcheck.web import app as web
    web._cache.clear()
    yield
    web._cache.clear()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from netcheck.web.app import app
    c = TestClient(app)
    c.get("/api/scans")   # like a real browser: load a page first (sets the session cookie, web/security.py)
    return c


def _same_keys(ours, example, path="$"):
    if isinstance(example, dict):
        assert isinstance(ours, dict), path
        assert list(ours) == list(example), f"{path}: keys {list(ours)} != contract {list(example)}"
        for k in example:
            _same_keys(ours[k], example[k], f"{path}.{k}")
    elif isinstance(example, list) and example and ours:
        for item in ours:
            _same_keys(item, example[0], f"{path}[]")


def _save(*paths):
    with history.open_history() as conn:
        return [history.save(conn, analyze_file(p))[0] for p in paths]


# ------------------------------------------------------------------ MAC masking (one rule everywhere)
def test_mask_mac_keeps_only_last_two_bytes():
    assert mask_mac("aa:bb:cc:dd:ee:ff") == "XX:XX:XX:XX:EE:FF"
    assert mask_mac("aa-bb-cc-dd-e-f") == "XX:XX:XX:XX:0E:0F"
    assert mask_mac(None) is None and mask_mac("") is None
    assert mask_mac("garbage") == mask_mac("zz:bb:cc:dd:ee:ff") == "XX:XX:XX:XX:XX:XX"
    assert mask_mac(mask_mac("14:cc:20:11:1a:2b")) == "XX:XX:XX:XX:1A:2B"       # idempotent


# ------------------------------------------------------------------ §2 / §4 builders
@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_evaluated_scan_matches_contract_section2(path):
    a = analyze_file(path)
    payload = contract.evaluated_scan(a)
    _same_keys(payload, EVALUATED)
    assert payload["network_score"] == a.score and len(payload["findings"]) == len(a.findings)
    assert all(d["mac_masked"] is None or d["mac_masked"].startswith("XX:XX:XX:XX:") for d in payload["devices"])


def test_evaluated_scan_for_broken_file():
    ev = contract.evaluated_scan(analyze_file(SYN / "V7_broken.xml"))
    assert ev["network_score"] is None and ev["error"] and ev["findings"] == []


def test_delta_matches_contract_section4():
    a, b = analyze_file(SYN / "V6a_before.xml"), analyze_file(SYN / "V6b_after.xml")
    payload = contract.delta(compare(a, b), a, b)
    _same_keys(payload, DELTA)
    assert payload["score_trend"] == {"previous_score": 60, "current_score": 100, "improved": True}
    assert len(payload["deltas"]["resolved_findings"]) == 3
    assert (payload["previous_scan_id"], payload["current_scan_id"]) == ("V6a_before", "V6b_after")


# ------------------------------------------------------------------ history round trip
@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_history_load_analysis_gives_same_contract(path):
    """What the UI/API rebuild from SQLite equals what the Rule Engine produced from the file."""
    (sid,) = _save(path)
    with history.open_history() as conn:
        again = history.load_analysis(conn, sid)
    assert contract.evaluated_scan(again) == contract.evaluated_scan(analyze_file(path))


# ------------------------------------------------------------------ JSON API
def test_api_serves_contract_payloads(client):
    i, j = _save(SYN / "V6a_before.xml", SYN / "V6b_after.xml")
    listing = client.get("/api/scans").json()
    assert [(s["id"], s["scan_id"], s["network_score"]) for s in listing] == [(i, "V6a_before", 60), (j, "V6b_after", 100)]

    ev = client.get(f"/api/scans/{i}").json()
    _same_keys(ev, EVALUATED)
    assert ev == json.loads(json.dumps(contract.evaluated_scan(analyze_file(SYN / "V6a_before.xml"))))
    assert client.get("/api/scans/latest").json()["scan_id"] == "V6b_after"

    d = client.get(f"/api/scans/{j}/delta").json()
    _same_keys(d, DELTA)
    assert d["score_trend"] == {"previous_score": 60, "current_score": 100, "improved": True}
    assert len(d["deltas"]["resolved_findings"]) == 3
    assert client.get(f"/api/scans/{j}/delta?previous={i}").json() == d


def test_api_errors(client):
    assert client.get("/api/scans").json() == []
    assert client.get("/api/scans/latest").status_code == 404
    assert client.get("/api/scans/999").status_code == 404
    assert client.get("/api/scans/abc").status_code == 422
    (sid,) = _save(SYN / "V1_home_basic.xml")
    assert client.get(f"/api/scans/{sid}/delta").status_code == 404           # nothing earlier
    assert client.get(f"/api/scans/{sid}/delta?previous=999").status_code == 404


def test_api_never_returns_full_macs(client):
    a = analyze_file(SYN / "V2_smart_home.xml")
    full = [h.mac.upper() for h in a.scan.hosts if h.mac]
    assert full
    (sid,) = _save(SYN / "V2_smart_home.xml")
    body = client.get(f"/api/scans/{sid}").text.upper()
    assert not any(m in body for m in full)


# ------------------------------------------------------------------ the page's actions (/api/v1)
def test_ask_falls_back_to_built_in_text(client):
    _save(SYN / "V3_small_office.xml")
    r = client.post("/api/v1/ask?lang=en", json={"question": "What do I fix first?"})
    assert r.status_code == 200 and r.json()["mode"] == "offline" and r.json()["answer"]


def test_ui_delete_history(client):
    _save(SYN / "V1_home_basic.xml")
    client.delete("/api/v1/history")
    assert client.get("/api/scans").json() == []
