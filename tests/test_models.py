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
