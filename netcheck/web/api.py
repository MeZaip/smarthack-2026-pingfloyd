"""Read-only JSON API over the local scan history, in the formats of service_data_contracts.md.

  GET /api/scans                               list of saved scans, in the order they were saved
  GET /api/scans/latest                        §2 Evaluated Scan Data, most recent scan
  GET /api/scans/{id}                          §2 Evaluated Scan Data
  GET /api/scans/{id}/delta[?previous=<id>]    §4 History & Deltas (default: the scan just before it)

Runs inside the web app (127.0.0.1, unprivileged). Payloads are built only by netcheck/core/contract.py.
Unreadable files are never saved to the history, so they do not appear here (they get ERROR in scores.csv).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from .. import history
from ..core import contract

router = APIRouter(prefix="/api", tags=["api"])


def _analysis(conn, scan_id: int):
    from .app import get_analysis   # deferred: app imports this module
    try:
        return get_analysis(conn, scan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"scan {scan_id} not found") from None


@router.get("/scans")
def list_scans() -> list[dict]:
    with history.open_history() as conn:
        return [{
            "id": s["scan_id"],
            "scan_id": contract.scan_id(s["file"]),
            "scanned_at": s["scanned_at"],
            "saved_at": s["saved_at"],
            "network_score": s["network_score"],
        } for s in history.trend(conn)]


@router.get("/scans/latest")
def latest_scan() -> dict:
    with history.open_history() as conn:
        ids = history.scan_ids(conn)
        if not ids:
            raise HTTPException(status_code=404, detail="no scan in history yet")
        return contract.evaluated_scan(_analysis(conn, ids[-1]))


@router.get("/scans/{scan_id}")
def get_scan(scan_id: int) -> dict:
    with history.open_history() as conn:
        return contract.evaluated_scan(_analysis(conn, scan_id))


@router.get("/scans/{scan_id}/delta")
def get_delta(scan_id: int, previous: Optional[int] = None) -> dict:
    with history.open_history() as conn:
        after = _analysis(conn, scan_id)
        prev_id = previous if previous is not None else history.previous_id(conn, scan_id)
        if prev_id is None:
            raise HTTPException(status_code=404, detail=f"scan {scan_id} has no earlier scan to compare with")
        before = _analysis(conn, prev_id)
        return contract.delta(history.changes(conn, prev_id, scan_id), before, after)
