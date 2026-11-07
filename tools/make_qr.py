"""QR code for the online demo (slide / poster). Dev tool: pip install segno.

    python tools/make_qr.py [URL] [--out docs/qr-demo]   -> docs/qr-demo.png + docs/qr-demo.svg
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEMO_URL = "https://stevenenson.github.io/netcheck-demo/"


def main(argv=None) -> int:
    import segno
    p = argparse.ArgumentParser()
    p.add_argument("url", nargs="?", default=DEMO_URL)
    p.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "docs" / "qr-demo"))
    a = p.parse_args(argv)
    qr = segno.make(a.url, error="h")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    qr.save(str(out) + ".png", scale=16, border=4, dark="#140c10", light="#ffffff")
    qr.save(str(out) + ".svg", scale=16, border=4, dark="#140c10", light="#ffffff", title="netcheck demo")
    print(f"Wrote {out}.png and {out}.svg for {a.url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
