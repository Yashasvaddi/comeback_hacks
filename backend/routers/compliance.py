"""Compliance intelligence endpoints — scan, gaps, report."""
from __future__ import annotations

from fastapi import APIRouter

from agents.compliance import run_compliance_scan

router = APIRouter()

# Cache the last scan so /gaps and /report don't re-run the LLM each call.
_last_report = None


@router.get("/scan")
async def scan() -> dict:
    global _last_report
    report = await run_compliance_scan()
    _last_report = report
    return report.model_dump()


@router.get("/gaps")
async def gaps() -> dict:
    if _last_report is None:
        return {"gaps": [], "detail": "run /api/compliance/scan first"}
    return {"gaps": [g.model_dump() for g in _last_report.gaps if g.status != "met"]}


@router.get("/report")
async def report() -> dict:
    if _last_report is None:
        return {"report": None, "detail": "run /api/compliance/scan first"}
    return _last_report.model_dump()
