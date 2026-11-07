"""The CLI module must speak exactly the JSON formats in service_data_contracts.md."""
import json
import os
import re
from pathlib import Path

import pytest

os.environ["NETCHECK_OFFLINE"] = "1"

from netcheck import cli, contracts  # noqa: E402
from netcheck.analyzer import analyze_file, list_scan_files, write_csvs, analyze_folder  # noqa: E402
from netcheck.parser import ScanFileError, parse_file  # noqa: E402
from netcheck.rules import classify  # noqa: E402

REPO = Path(__file__).parent.parent
ROOT = Path(__file__).parent / "fixtures"
V = ROOT / "validation" if (ROOT / "validation").is_dir() and any((ROOT / "validation").glob("*.xml")) \
    else ROOT / "validation_synthetic"
GOOD = [p for p in list_scan_files(V) if "broken" not in p.name]


@pytest.fixture(autouse=True)
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCHECK_HOME", str(tmp_path / "home"))


def _examples() -> list[dict]:
    text = (REPO / "service_data_contracts.md").read_text(encoding="utf-8")
    return [json.loads(b) for b in re.findall(r"```json\n(.*?)```", text, re.S)]


RAW, EVALUATED, _LLM_REQ, _LLM_RESP, DELTA = _examples()


def _shape(x):
    """Structure of a JSON value: dict -> {key: shape}, list -> [shape of first item], scalar -> None."""
    if isinstance(x, dict):
        return {k: _shape(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_shape(x[0])] if x else []
    return None


def _same_keys(ours, example, path="$"):
    if isinstance(example, dict):
        assert isinstance(ours, dict), path
        assert list(ours) == list(example), f"{path}: keys {list(ours)} != contract {list(example)}"
        for k in example:
            _same_keys(ours[k], example[k], f"{path}.{k}")
    elif isinstance(example, list) and example and ours:
        for item in ours:
            _same_keys(item, example[0], f"{path}[]")


def test_contract_doc_has_the_expected_sections():
    assert set(RAW) == {"scan_id", "timestamp", "network", "devices"}
    assert "finding_code" in EVALUATED["findings"][0] and "score_trend" in DELTA


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_raw_payload_matches_contract_section1(path):
    _same_keys(contracts.raw_from_file(path), RAW)


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_evaluated_payload_matches_contract_section2(path):
    r = analyze_file(path)
    payload = contracts.evaluated_scan(r, parse_file(path))
    _same_keys(payload, EVALUATED)
    assert payload["network_score"] == r.score
    assert len(payload["findings"]) == len(r.findings)


def test_delta_matches_contract_section4():
    a, b = V / "V6a_before.xml", V / "V6b_after.xml"
    payload = contracts.delta(analyze_file(a), analyze_file(b), parse_file(a), parse_file(b))
    _same_keys(payload, DELTA)
    assert payload["score_trend"] == {"previous_score": 60, "current_score": 100, "improved": True}
    assert len(payload["deltas"]["resolved_findings"]) == 3      # brief: "history must show 3 resolved"
    assert payload["previous_scan_id"] == "V6a_before" and payload["current_scan_id"] == "V6b_after"


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_rule_engine_gives_same_findings_from_contract(path):
    """§1 carries everything the rules need: XML path and contract path must agree exactly."""
    key = lambda fs: sorted((f.ip, f.port, f.code, f.severity) for f in fs)  # noqa: E731
    direct = classify(path.name, parse_file(path))
    via_contract = classify(path.name, contracts.hosts_from_raw(json.loads(json.dumps(contracts.raw_from_file(path)))))
    assert key(via_contract) == key(direct)


def test_https_is_marked_so_rules_skip_it():
    raw = contracts.raw_from_file(V / "V1_home_basic.xml")
    ports = {p["port"]: p for d in raw["devices"] for p in d["open_ports"]}
    assert ports[443]["service"] == "ssl/http" and ports[80]["service"] == "http"


def test_mac_masking_follows_contract():
    assert contracts.mask_mac("14:cc:20:11:1a:2b") == "XX:XX:XX:XX:1A:2B"
    assert contracts.mask_mac("") is None
    assert contracts.mask_mac("garbage") == "XX:XX:XX:XX:XX:XX"
    dump = json.dumps(contracts.raw_from_file(V / "V2_smart_home.xml"))
    assert "C0:06:C3" not in dump.upper()                           # first bytes never leave
    assert re.findall(r'"mac_masked": "XX:XX:XX:XX:[0-9A-F]{2}:[0-9A-F]{2}"', dump)


def test_metadata_and_nulls():
    raw = contracts.raw_from_file(V / "V4_legacy.xml")
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", raw["timestamp"])
    assert raw["network"] == {"subnet": "192.168.1.0/24", "gateway": None}   # gateway only known live
    unknown = next(d for d in raw["devices"] if d["ip"].endswith(".99"))
    assert unknown["vendor"] is None and unknown["hostname"] is None


def test_broken_file():
    with pytest.raises(ScanFileError):
        contracts.raw_from_file(V / "V7_broken.xml")
    ev = contracts.evaluated_scan(analyze_file(V / "V7_broken.xml"))
    assert ev["network_score"] is None and ev["error"] and ev["findings"] == []


@pytest.mark.parametrize("bad", [
    [], {"devices": "x"}, {"devices": [1]}, {"devices": [{"ip": "evil"}]},
    {"devices": [{"ip": "10.0.0.1", "open_ports": [{"port": "80", "protocol": "tcp"}]}]},
    {"devices": [{"ip": "10.0.0.1", "open_ports": [{"port": 70000, "protocol": "tcp"}]}]},
    {"devices": [{"ip": "10.0.0.1", "open_ports": [{"port": 80, "protocol": "icmp"}]}]},
    {"devices": [{"ip": "10.0.0.1", "vendor": {"x": 1}}]},
])
def test_hostile_raw_payload_rejected(bad):
    with pytest.raises(contracts.ContractError):
        contracts.hosts_from_raw(bad)


# ------------------------------------------------------------------ CLI commands
def test_cli_parse_folder_writes_contract_files(tmp_path, capsys):
    assert cli.main(["parse", str(V), "--out", str(tmp_path)]) == 0
    written = sorted(p.name for p in tmp_path.glob("*.raw.json"))
    assert len(written) == len(GOOD) and "V7_broken.raw.json" not in written
    assert "V7_broken.xml: ERROR" in capsys.readouterr().err


def test_cli_parse_stdout_is_json(capsys):
    assert cli.main(["parse", str(V / "V3_small_office.xml")]) == 0
    assert json.loads(capsys.readouterr().out)["scan_id"] == "V3_small_office"


def test_cli_diff_json(capsys):
    assert cli.main(["diff", str(V / "V6a_before.xml"), str(V / "V6b_after.xml"), "--json"]) == 0
    _same_keys(json.loads(capsys.readouterr().out), DELTA)


def test_cli_analyze_contracts_keeps_csvs_identical(tmp_path):
    plain, withc = tmp_path / "plain", tmp_path / "withc"
    write_csvs(analyze_folder(V), plain)
    assert cli.main(["analyze", str(V), "--out", str(withc), "--contracts"]) == 0
    for name in ("findings.csv", "scores.csv"):
        assert (plain / name).read_bytes() == (withc / name).read_bytes()
    assert (withc / "contracts" / "V7_broken.evaluated.json").exists()
    assert not (withc / "contracts" / "V7_broken.raw.json").exists()


def test_cli_detect_json(monkeypatch, capsys):
    from netcheck import netdetect
    monkeypatch.setattr(netdetect, "detect", lambda: netdetect.NetworkInfo(
        "en0", "172.20.10.2", "255.255.255.240", "172.20.10.0/28", "172.20.10.1"))
    assert cli.main(["detect", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["network"] == {"subnet": "172.20.10.0/28", "gateway": "172.20.10.1"}
    _same_keys(out["network"], RAW["network"])
