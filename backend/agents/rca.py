"""Maintenance Root-Cause Analysis agent.

Pulls an asset's graph neighborhood (incidents, procedures, people) and the
most relevant document evidence, then asks gpt-oss:120b-cloud to produce a
structured RCA report (immediate cause → contributing factors → root causes →
recommendations → similar incidents).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from graph.queries import get_asset_subgraph
from llm import Tier, complete_json
from vector_store.qdrant_store import search as vector_search


class RCAReport(BaseModel):
    asset_tag: str
    summary: str = ""
    immediate_cause: str = ""
    contributing_factors: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    similar_incidents: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: list[dict] = Field(default_factory=list)


_SYSTEM = (
    "You are a senior reliability engineer performing root-cause analysis on "
    "industrial rotating/static equipment. Use ONLY the supplied evidence "
    "(maintenance history, inspection readings, graph relationships). Produce a "
    "rigorous, structured RCA. Do not invent failures not supported by evidence."
)

_SCHEMA = """Return ONLY JSON:
{
  "summary": "1-2 sentence overview of the failure and its resolution",
  "immediate_cause": "the proximate cause",
  "contributing_factors": ["..."],
  "root_causes": ["the underlying systemic causes"],
  "recommendations": ["specific, actionable preventive actions"],
  "similar_incidents": ["references to comparable past incidents if any"]
}"""


async def run_rca(asset_tag: str) -> RCAReport:
    asset_tag = asset_tag.strip().upper()

    subgraph = await get_asset_subgraph(asset_tag)
    chunks = vector_search(f"{asset_tag} failure root cause maintenance history", top_k=8)

    # Assemble evidence text.
    evidence_lines: list[str] = []
    if subgraph.get("found"):
        eq = subgraph.get("equipment") or {}
        evidence_lines.append(
            f"ASSET: {asset_tag} — {eq.get('name','')} (type {eq.get('type','?')}, "
            f"location {eq.get('location','?')})"
        )
        for nb in subgraph.get("neighbors", []):
            evidence_lines.append(f"  graph: {nb['rel']} → ({nb['label']}) {nb['key']}")
    for i, c in enumerate(chunks, 1):
        evidence_lines.append(f"[{i}] {c.get('title','')}: {c.get('text','')[:600]}")

    evidence_text = "\n".join(evidence_lines) or "(no evidence found for this asset)"

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"{_SCHEMA}\n\n---\nEVIDENCE FOR {asset_tag}:\n{evidence_text}"},
    ]
    data = await complete_json(messages=messages, tier=Tier.SMART)
    if not isinstance(data, dict):
        data = {}

    # Confidence: evidence-driven.
    conf = 0.0
    if chunks:
        conf += min(0.6, float(chunks[0].get("score", 0)) )
    if subgraph.get("found"):
        conf += 0.3

    return RCAReport(
        asset_tag=asset_tag,
        summary=data.get("summary", ""),
        immediate_cause=data.get("immediate_cause", ""),
        contributing_factors=list(data.get("contributing_factors", []) or []),
        root_causes=list(data.get("root_causes", []) or []),
        recommendations=list(data.get("recommendations", []) or []),
        similar_incidents=list(data.get("similar_incidents", []) or []),
        confidence=round(min(1.0, conf), 2),
        evidence=[
            {"title": c.get("title", ""), "document_id": c.get("document_id"),
             "score": round(float(c.get("score", 0)), 3)}
            for c in chunks
        ],
    )
