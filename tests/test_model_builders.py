"""Procedural device models (ui/assets/models/procedural/): valid, and loaded by the app and the lab page."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "ui" / "assets" / "models" / "procedural"
KEYS = sorted(p.stem for p in PROC.glob("*.js") if p.stem != "kit")


def test_there_are_procedural_models():
    assert {"computer-macbook", "computer-imac", "phone-iphone", "phone-android", "iot-raspberrypi"} <= set(KEYS)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")
def test_models_follow_the_rules():
    r = subprocess.run(["node", str(ROOT / "tools" / "check_builders.mjs")], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("page, prefix", [("ui/index.html", "assets/models/procedural/"), ("ui/assets/models/lab.html", "procedural/")])
def test_every_model_is_loaded_before_device3d(page, prefix):
    html = (ROOT / page).read_text(encoding="utf-8")
    device3d = html.index("device3d.js")
    kit = html.index(f'src="{prefix}kit.js"')
    for key in KEYS:
        at = html.index(f'src="{prefix}{key}.js"')
        assert kit < at < device3d, f"{page}: {key}.js must load after kit.js and before device3d.js"


def test_every_variant_has_a_base_type_model():
    """A variant falls back to the .glb of its base type ("phone-iphone" -> phone.glb) when WebGL code fails."""
    from netcheck.core.device import DEVICE_LABELS
    for key in KEYS:
        assert key.split("-")[0] in DEVICE_LABELS, key
