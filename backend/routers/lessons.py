"""Lessons Learned endpoints — failure patterns + similar-incident search."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agents.lessons import discover_patterns, find_similar

router = APIRouter()


class LessonSearch(BaseModel):
    query: str


@router.get("/patterns")
async def patterns() -> dict:
    pats = await discover_patterns()
    return {"patterns": [p.model_dump() for p in pats]}


@router.post("/search")
async def search(body: LessonSearch) -> dict:
    return {"query": body.query, "results": await find_similar(body.query)}
