"""Data-contract payloads produced by the Rule Engine / Data Layer (service_data_contracts.md).

  §2 Evaluated Scan Data  (Rule Engine -> UI / DB)   evaluated_scan(analysis)
  §4 History & Deltas     (Database -> UI)           delta(changes, before, after)

§1 (Raw Parsed Data) is built by netcheck/net/contract.py; §3 (LLM enrichment) by the LLM service.
Deterministic: no LLM, no clock, no randomness. Unknown strings are null, never "".
An unreadable file in §2 gets "network_score": null plus an "error" message.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .analysis import Analysis


def scan_id(file_name: str) -> str:
    return Path(file_name).stem


def _null(s: Optional[str]) -> Optional[str]:
    return s or None


def evaluated_scan(a: Analysis) -> dict:
    """Analysis -> §2 payload."""
    if not a.ok:
        return {"scan_id": scan_id(a.file), "network_score": None, "error": a.error,
                "devices": [], "findings": []}
    return {
        "scan_id": scan_id(a.file),
        "network_score": a.score,
        "devices": [{
            "ip": d["ip"],
            "mac_masked": d["mac"],                 # already masked by Analysis.devices()
            "vendor": _null(d["vendor"]),
            "hostname": _null(d["hostname"]),
            "device_type_guess": d["type"],
        } for d in sorted(a.devices(), key=lambda d: _ip_sort(d["ip"]))],
        "findings": [{
            "ip": f.ip,
            "port": f.port,
            "finding_code": f.code,
            "severity": f.severity,
            "points": f.points,
            "evidence": f.evidence,
        } for f in sorted(a.findings, key=lambda f: f.sort_key)],
    }


def delta(changes: dict, before: Analysis, after: Analysis,
          before_id: Optional[str] = None, after_id: Optional[str] = None) -> dict:
    """core.diff / history.changes() result (+ both analyses, for masked MACs) -> §4 payload."""
    macs_before = {d["ip"]: d["mac"] for d in before.devices()}
    macs_after = {d["ip"]: d["mac"] for d in after.devices()}

    def fnd(x: dict) -> dict:
        return {"ip": x["ip"], "port": x["port"], "finding_code": x["code"]}

    return {
        "current_scan_id": after_id or scan_id(after.file),
        "previous_scan_id": before_id or scan_id(before.file),
        "score_trend": {
            "previous_score": changes["score_before"],
            "current_score": changes["score_after"],
            "improved": changes["score_after"] > changes["score_before"],
        },
        "deltas": {
            "new_devices": [{"ip": ip, "mac_masked": macs_after.get(ip)} for ip in changes["new_devices"]],
            "removed_devices": [{"ip": ip, "mac_masked": macs_before.get(ip)} for ip in changes["removed_devices"]],
            "new_findings": [fnd(x) for x in changes["new_findings"]],
            "resolved_findings": [fnd(x) for x in changes["resolved_findings"]],
        },
    }


def _ip_sort(ip: str):
    from .models import _ip_key
    return _ip_key(ip)
