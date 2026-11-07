"""The demo UI data is generated from the real analyser and never contains a full MAC address."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_export_ui_data(tmp_path):
    out = tmp_path / "data.js"
    subprocess.run([sys.executable, str(ROOT / "tools" / "export_ui_data.py"), "--out", str(out)], check=True,
                   capture_output=True)
    js = out.read_text(encoding="utf-8")
    data = json.loads(js[js.index("=") + 1:].rstrip().rstrip(";"))
    scans = {s["file"]: s for s in data["scans"]}
    assert scans["V2_smart_home.xml"]["score"] == 40
    assert scans["V2_smart_home.xml"]["findings"][0]["code"] == "CAMERA_STREAM_EXPOSED"
    assert "error" in scans["V7_broken.xml"]
    assert data["history"]["changes"]["score_change"] == 40
    full_mac = re.compile(r"\b(?:[0-9A-F]{2}:){5}[0-9A-F]{2}\b", re.I)
    assert not full_mac.search(js.replace(":XX:XX:XX", "")), "full MAC address leaked into ui/data.js"
    assert "</script" not in js.lower()
