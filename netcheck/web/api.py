"""Read-only JSON API over the scan history, in the formats of service_data_contracts.md.

  GET /api/scans[?source=]                     list of stored scans
  GET /api/scans/latest                        §2 Evaluated Scan Data, latest readable scan
  GET /api/scans/{id}                          §2 Evaluated Scan Data
  GET /api/scans/{id}/delta[?previous=<id>]    §4 History & Deltas (default: previous readable scan, same source)

Runs inside `netcheck serve` (127.0.0.1, unprivileged). Payloads are built only by netcheck/contracts.py.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import contracts, history
from ..models import ScanResult

router = APIRouter(prefix="/api", tags=["api"])


def _load(scan_id: int) -> ScanResult:
    r = history.load(scan_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"scan {scan_id} not found")
    return r


@router.get("/scans")
def list_scans(source: str | None = None) -> list[dict]:
    return [{
        "id": s["id"],
        "scan_id": contracts.scan_id(s["file"]),
        "created_at": s["created_at"],
        "source": s["source"],
        "network_score": s["score"] if s["ok"] else None,
    } for s in history.list_scans(source)]


@router.get("/scans/latest")
def latest_scan() -> dict:
    sid = history.latest_id()
    if sid is None:
        raise HTTPException(status_code=404, detail="no readable scan in history yet")
    return contracts.evaluated_scan(_load(sid))


@router.get("/scans/{scan_id}")
def get_scan(scan_id: int) -> dict:
    return contracts.evaluated_scan(_load(scan_id))


@router.get("/scans/{scan_id}/delta")
def get_delta(scan_id: int, previous: int | None = None) -> dict:
    current = _load(scan_id)
    prev_id = previous if previous is not None else history.previous_of(scan_id)
    if prev_id is None:
        raise HTTPException(status_code=404, detail=f"scan {scan_id} has no earlier scan to compare with")
    prev = _load(prev_id)
    for sid, r in ((scan_id, current), (prev_id, prev)):
        if not r.ok:
            raise HTTPException(status_code=422, detail=f"scan {sid} could not be read: {r.error}")
    return contracts.delta(prev, current)
