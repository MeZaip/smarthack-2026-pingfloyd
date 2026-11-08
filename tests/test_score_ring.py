"""Score dial (ui/assets/score-ring/): its files, the font licence, and how the app loads it."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RING = ROOT / "ui" / "assets" / "score-ring"


def test_files_are_there():
    for name in ("score-ring.js", "score-ring.css", "demo.html", "fonts/orbitron-latin.woff2", "fonts/OFL.txt"):
        assert (RING / name).is_file(), name
    assert (RING / "fonts" / "orbitron-latin.woff2").read_bytes()[:4] == b"wOF2"
    assert "SIL Open Font License" in (RING / "fonts" / "OFL.txt").read_text(encoding="utf-8")


def test_font_is_local_not_a_cdn():
    """The app works offline and sends nothing to a font server."""
    css = (RING / "score-ring.css").read_text(encoding="utf-8")
    assert 'url("fonts/orbitron-latin.woff2")' in css
    assert "googleapis" not in css and "gstatic" not in css


def test_app_loads_the_dial_before_app_js():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    assert 'href="assets/score-ring/score-ring.css"' in html
    assert html.index('src="assets/score-ring/score-ring.js"') < html.index('src="app.js"')
    app = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    assert "ScoreRing.create(" in app and "ScoreRing.pending(" in app
