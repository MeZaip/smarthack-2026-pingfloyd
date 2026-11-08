"""Download the two free Piper voices used by the assistant's voice mode (netcheck/ai/local_tts.py).

    python tools/get_voices.py            # -> voices/piper/ (git-ignored)

Source: https://huggingface.co/rhasspy/piper-voices (open voice models). About 60 MB per voice.
Each file is downloaded to a temporary name and only kept if it is complete (size and SHA-256 checked when the
repository publishes them; otherwise at least the size reported by the server).
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from netcheck.ai.local_tts import VOICES, voices_dir  # noqa: E402

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
PATHS = {"ro": "ro/ro_RO/mihai/medium", "en": "en/en_US/lessac/medium"}


def fetch(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as fh:
        want = int(r.headers.get("Content-Length") or 0)
        got, h = 0, hashlib.sha256()
        while chunk := r.read(1 << 16):
            fh.write(chunk); h.update(chunk); got += len(chunk)
    if want and got != want:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"incomplete download: {dest.name} ({got} of {want} bytes)")
    tmp.replace(dest)
    print(f"  {dest.name}: {got / 1e6:.1f} MB, sha256 {h.hexdigest()[:16]}…")


def main() -> int:
    out = voices_dir()
    out.mkdir(parents=True, exist_ok=True)
    for lang, name in VOICES.items():
        for suffix in (".onnx.json", ".onnx"):
            dest = out / f"{name}{suffix}"
            if dest.is_file() and dest.stat().st_size > 0:
                print(f"  {dest.name}: already here")
                continue
            fetch(f"{BASE}/{PATHS[lang]}/{name}{suffix}", dest)
    print(f"Voices in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
