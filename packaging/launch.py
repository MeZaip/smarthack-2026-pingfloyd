"""Entry point of the packaged app (netcheck.app / netcheck.exe)."""
import sys

from netcheck.app import main

if __name__ == "__main__":
    sys.exit(main([]))
