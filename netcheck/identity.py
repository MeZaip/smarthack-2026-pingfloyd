"""Local-only secrets and privacy-preserving device IDs.

device_id = HMAC-SHA256(local secret, full MAC or IP)[:12]
  -> the same device is recognised across scans (nicknames, watch mode)
  -> the MAC itself is never stored or shown, and the ID is useless on another machine.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path


def home_dir() -> Path:
    p = Path(os.environ.get("NETCHECK_HOME") or (Path.home() / ".netcheck"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def private_file(name: str, create: callable) -> bytes:
    """Read a 0600 file from the NetCheck home, creating it once with create() if missing."""
    path = home_dir() / name
    if not path.exists():
        data = create()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
    return path.read_bytes()


def _secret() -> bytes:
    return private_file("secret", lambda: secrets.token_bytes(32))


def device_id(mac: str, ip: str) -> str:
    basis = f"mac:{mac.upper()}" if mac else f"ip:{ip}"
    return hmac.new(_secret(), basis.encode(), hashlib.sha256).hexdigest()[:12]
