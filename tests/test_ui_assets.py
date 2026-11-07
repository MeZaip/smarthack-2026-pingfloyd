"""UI source checks: no emoji in the interface (SVG icons only), Three.js bundled locally with its licence."""
import re
from pathlib import Path

UI = Path(__file__).resolve().parent.parent / "ui"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿️]")


def test_no_emoji_in_ui_sources():
    for name in ("index.html", "app.js", "styles.css", "safehouse3d.js"):
        text = (UI / name).read_text(encoding="utf-8")
        hits = [ln for ln in text.splitlines() if EMOJI.search(ln)]
        assert not hits, f"{name} still has emoji: {hits[:3]}"


def test_every_icon_used_exists_in_the_sprite():
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    defined = set(re.findall(r'<symbol id="i-([a-z-]+)"', html))
    used = set(re.findall(r'icon\("([a-z-]+)"', js)) | set(re.findall(r'href="#i-([a-z-]+)"', html))
    used |= set(re.findall(r'icon: "([a-z-]+)"', js)) | set(re.findall(r':\s*"([a-z-]+)"', js.split("const DEVICE_ICON")[1].split(";")[0]))
    missing = used - defined
    assert not missing, f"icons used but not defined: {sorted(missing)}"


def test_three_is_local_and_licensed():
    assert (UI / "vendor" / "three.min.js").stat().st_size > 500_000
    assert "MIT License" in (UI / "vendor" / "three.LICENSE").read_text(encoding="utf-8")
    html = (UI / "index.html").read_text(encoding="utf-8")
    assert "http://" not in html.replace("http://www.w3.org", "") and "https://" not in html, "no external resources"
