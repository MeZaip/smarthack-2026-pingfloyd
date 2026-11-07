# PyInstaller spec for the desktop app.   Build:  pyinstaller packaging/netcheck.spec
#   macOS   -> dist/netcheck.app      Windows -> dist/netcheck.exe
# Bundles: the netcheck package, ui/ (page, styles, script) and the example scans. nmap is NOT bundled:
# the app shows how to install it once (nmap's licence does not allow free redistribution inside other apps).
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
datas = [(str(ROOT / "ui" / f), "ui") for f in ("index.html", "app.js", "styles.css")]
datas += [(str(p), "tests/fixtures/synthetic") for p in (ROOT / "tests" / "fixtures" / "synthetic").glob("*.xml")]

optional = []
try:
    import psutil  # noqa: F401  (network detection on Windows)
    optional.append("psutil")
except ImportError:
    pass

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=collect_submodules("netcheck") + ["segno", "defusedxml", "defusedxml.ElementTree"] + optional,
    excludes=["tkinter", "pytest", "gateway"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="netcheck", console=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="netcheck")
    app = BUNDLE(coll, name="netcheck.app", bundle_identifier="ro.pingfloyd.netcheck",
                 info_plist={"CFBundleDisplayName": "netcheck", "CFBundleShortVersionString": "1.0.0",
                             "LSUIElement": False, "NSHighResolutionCapable": True})
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="netcheck", console=False)
