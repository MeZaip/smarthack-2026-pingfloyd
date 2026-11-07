"""Signed before/after certificate (Ed25519).

The private key is created once in ~/.netcheck/signing_key (0600) and never leaves the laptop.
Anyone with the certificate JSON can check it was not altered: change one number and verification fails.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

from .identity import private_file
from .models import ScanResult

CERT_TYPE = "netcheck-before-after-certificate"


def _private_key() -> Ed25519PrivateKey:
    raw = private_file("signing_key", lambda: Ed25519PrivateKey.generate().private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
    return Ed25519PrivateKey.from_private_bytes(raw)


def _pub_raw(pub: Ed25519PublicKey) -> bytes:
    return pub.public_bytes(Encoding.Raw, PublicFormat.Raw)


def fingerprint(pub_raw: bytes) -> str:
    h = hashlib.sha256(pub_raw).hexdigest()[:16].upper()
    return " ".join(h[i:i + 4] for i in range(0, 16, 4))


def local_fingerprint() -> str:
    return fingerprint(_pub_raw(_private_key().public_key()))


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _side(r: ScanResult, scanned_at: str) -> dict:
    return {
        "file": r.file, "sha256": r.file_sha256, "scanned_at": scanned_at, "score": r.score,
        "devices": len(r.devices),
        "findings": [{"ip": f.ip, "port": f.port, "code": f.code, "severity": f.severity} for f in r.findings],
    }


def build(before: ScanResult, after: ScanResult, before_at: str, after_at: str) -> dict:
    bk = {(f.ip, f.port, f.code): f for f in before.findings}
    ak = {(f.ip, f.port, f.code): f for f in after.findings}
    payload = {
        "type": CERT_TYPE, "version": 1,
        "issued_at": datetime.now().isoformat(timespec="seconds"),
        "before": _side(before, before_at), "after": _side(after, after_at),
        "score_delta": (after.score or 0) - (before.score or 0),
        "resolved": [{"ip": k[0], "port": k[1], "code": k[2]} for k in sorted(set(bk) - set(ak), key=str)],
        "new": [{"ip": k[0], "port": k[1], "code": k[2]} for k in sorted(set(ak) - set(bk), key=str)],
        "note": "Standard NetCheck score = max(0, 100 - sum of finding points). MAC addresses are not included.",
    }
    key = _private_key()
    pub = _pub_raw(key.public_key())
    return {
        "payload": payload,
        "signature": base64.b64encode(key.sign(canonical(payload))).decode(),
        "public_key": base64.b64encode(pub).decode(),
        "key_fingerprint": fingerprint(pub),
    }


def verify(cert: dict) -> tuple[bool, str, bool]:
    """Returns (valid, reason, issued_by_this_laptop)."""
    try:
        payload = cert["payload"]
        if payload.get("type") != CERT_TYPE:
            return False, "not a NetCheck certificate", False
        pub_raw = base64.b64decode(cert["public_key"], validate=True)
        sig = base64.b64decode(cert["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig, canonical(payload))
    except InvalidSignature:
        return False, "signature does not match: the certificate was altered", False
    except (KeyError, TypeError, ValueError, AttributeError):
        return False, "malformed certificate", False
    return True, "signature valid", fingerprint(pub_raw) == local_fingerprint()
