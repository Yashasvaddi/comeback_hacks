"""Compliance Intelligence — map evidence to regulations, detect gaps.

For each requirement in a built-in industrial checklist (OISD / PESO / Factory
Act), we retrieve the most relevant document evidence and ask gpt-oss:120b-cloud
to judge whether the requirement is met, partially met, or a gap — with a risk
score. The checklist keeps the assessment grounded and demo-stable.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from llm import Tier, complete_json
from vector_store.qdrant_store import search as vector_search

# Representative requirements across common Indian industrial frameworks.
CHECKLIST = [
    {"framework": "OISD-STD-105", "requirement": "Preventive maintenance program for rotating equipment with defined intervals"},
    {"framework": "OISD-STD-106", "requirement": "Pressure vessel and relief valve inspection & certification records"},
    {"framework": "PESO", "requirement": "Hazardous area classification and licensing for flammable storage/handling"},
    {"framework": "Factory Act 1948", "requirement": "Permit-to-work / lockout-tagout system for maintenance activities"},
    {"framework": "Factory Act 1948", "requirement": "Periodic safety inspections and worker PPE compliance records"},
    {"framework": "OISD-STD-118", "requirement": "Incident reporting, investigation, and root-cause closure process"},
]


class ComplianceGap(BaseModel):
    framework: str
    requirement: str
    status: str  # met | partial | gap
    risk: str    # high | medium | low
    finding: str
    evidence: list[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    gaps: list[ComplianceGap] = Field(default_factory=list)
    summary: str = ""
    score: int = 0  # 0-100 overall compliance posture


_SYSTEM = (
    "You are an industrial compliance auditor for Indian process plants (OISD, "
    "PESO, Factory Act). Given a requirement and retrieved document evidence, "
    "judge whether it is met, partially met, or a gap. Base the verdict ONLY on "
    "the evidence; absence of evidence is itself a potential gap. Return JSON."
)

_SCHEMA = """Return ONLY JSON:
{"status": "met|partial|gap", "risk": "high|medium|low", "finding": "1-2 sentence justification"}"""


async def _assess_one(item: dict) -> ComplianceGap:
    chunks = vector_search(item["requirement"], top_k=4)
    evidence = "\n".join(f"- {c.get('title','')}: {c.get('text','')[:400]}" for c in chunks)
    evidence = evidence or "(no related document evidence found)"

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content":
            f"{_SCHEMA}\n\nFRAMEWORK: {item['framework']}\n"
            f"REQUIREMENT: {item['requirement']}\n\nEVIDENCE:\n{evidence}"},
    ]
    data = await complete_json(messages=messages, tier=Tier.SMART)
    if not isinstance(data, dict):
        data = {}

    return ComplianceGap(
        framework=item["framework"],
        requirement=item["requirement"],
        status=data.get("status", "gap"),
        risk=data.get("risk", "medium"),
        finding=data.get("finding", ""),
        evidence=[c.get("title", "") for c in chunks if c.get("title")],
    )


async def run_compliance_scan() -> ComplianceReport:
    gaps = [await _assess_one(item) for item in CHECKLIST]

    met = sum(1 for g in gaps if g.status == "met")
    partial = sum(1 for g in gaps if g.status == "partial")
    score = int(100 * (met + 0.5 * partial) / max(1, len(gaps)))

    n_gaps = sum(1 for g in gaps if g.status == "gap")
    summary = (
        f"Assessed {len(gaps)} requirements: {met} met, {partial} partial, "
        f"{n_gaps} gaps. Overall posture {score}/100."
    )
    return ComplianceReport(gaps=gaps, summary=summary, score=score)
