"""Maintenance RCA endpoints — generate, list, and fetch structured reports."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.rca import run_rca
from db.database import get_db
from db.models import RCAReportRow

router = APIRouter()


class RCARequest(BaseModel):
    asset_tag: str
    incident_id: str | None = None


@router.post("/analyze")
async def analyze(req: RCARequest, db: AsyncSession = Depends(get_db)) -> dict:
    report = await run_rca(req.asset_tag)
    row = RCAReportRow(
        asset_tag=report.asset_tag,
        report=report.model_dump(),
        confidence=int(report.confidence * 100),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "report": report.model_dump()}


@router.get("/reports")
async def reports(db: AsyncSession = Depends(get_db)) -> dict:
    rows = await db.execute(select(RCAReportRow).order_by(RCAReportRow.created_at.desc()))
    items = rows.scalars().all()
    return {
        "reports": [
            {"id": r.id, "asset_tag": r.asset_tag, "confidence": r.confidence,
             "summary": (r.report or {}).get("summary", ""), "created_at": r.created_at.isoformat()}
            for r in items
        ]
    }


@router.get("/report/{report_id}")
async def report(report_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(RCAReportRow, report_id)
    if row is None:
        return {"report_id": report_id, "report": None}
    return {"id": row.id, "report": row.report}
