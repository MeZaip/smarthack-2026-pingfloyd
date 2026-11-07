"""Desktop app entry point: double-click netcheck.app / netcheck.exe, or `python -m netcheck app`.

Starts the local server and opens the browser. No terminal commands, no Python needed in the packaged app.
"""
from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    from .web.server import serve
    p = argparse.ArgumentParser(prog="netcheck app", description="netcheck desktop app")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--db", help="history database (default: $NETCHECK_DB or ~/.netcheck/history.sqlite)")
    p.add_argument("--scans", help="folder for scan files (default: ~/.netcheck/scans)")
    a = p.parse_args(argv)
    return serve(port=a.port, open_browser=not a.no_browser, db=a.db, scans_dir=a.scans)


if __name__ == "__main__":
    sys.exit(main())
