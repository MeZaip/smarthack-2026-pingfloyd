"""3D device models: one .glb per device type, all valid (see ui/assets/models/README.md)."""
import subprocess
import sys
from pathlib import Path

from netcheck.core.device import DEVICE_LABELS

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "ui" / "assets" / "models"


def test_every_device_type_has_a_model():
    missing = [t for t in DEVICE_LABELS if not (MODELS / f"{t}.glb").exists()]
    assert not missing, f"device types without a 3D model: {missing} (add ui/assets/models/<type>.glb)"


def test_models_follow_the_rules():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_models.py"), str(MODELS)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_bundle_matches_the_glb_files():
    """ui/assets/models/models-bundle.js (used from file://) must hold exactly the .glb files, byte for byte."""
    import base64
    import re
    js = (MODELS / "models-bundle.js").read_text(encoding="utf-8")
    found = dict(re.findall(r'^\s*(\w+): "data:model/gltf-binary;base64,([A-Za-z0-9+/=]+)"', js, re.M))
    assert set(found) == set(DEVICE_LABELS), sorted(set(DEVICE_LABELS) ^ set(found))
    for t, b64 in found.items():
        assert base64.b64decode(b64) == (MODELS / f"{t}.glb").read_bytes(), f"{t}: bundle is stale, run tools/make_models.py"
