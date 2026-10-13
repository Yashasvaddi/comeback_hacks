"""Lessons Learned engine — similar-incident search + failure-pattern discovery.

Similarity uses semantic search over the chunk corpus plus the Incident nodes in
the graph. Pattern discovery asks gpt-oss:120b-cloud to cluster the known
incidents into recurring failure themes with preventive lessons.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from graph.neo4j_client import run_read
from llm import Tier, complete_json
from vector_store.qdrant_store import search as vector_search


class Pattern(BaseModel):
    theme: str
    affected_assets: list[str] = Field(default_factory=list)
    description: str = ""
    lesson: str = ""
    occurrences: int = 0


async def _all_incidents() -> list[dict]:
    rows = await run_read(
        "MATCH (i:Incident) "
        "OPTIONAL MATCH (e:Equipment)-[:HAS_INCIDENT]->(i) "
        "RETURN i.description AS description, i.severity AS severity, "
        "i.date AS date, collect(DISTINCT e.tag) AS assets"
    )
    return rows


async def find_similar(query: str, top_k: int = 6) -> list[dict]:
    """Semantic search for incidents/failures similar to the query text."""
    hits = vector_search(query, top_k=top_k)
    return [
        {"title": h.get("title", ""), "text": h.get("text", "")[:300],
         "document_id": h.get("document_id"), "score": round(float(h.get("score", 0)), 3)}
        for h in hits
    ]


async def discover_patterns() -> list[Pattern]:
    incidents = await _all_incidents()
    if not incidents:
        return []

    listing = "\n".join(
        f"- [{i.get('severity','?')}] {i.get('description','')} "
        f"(assets: {', '.join(a for a in i.get('assets',[]) if a) or 'n/a'})"
        for i in incidents
    )

    messages = [
        {"role": "system", "content":
            "You are a reliability engineer building an organizational lessons-learned "
            "repository. Cluster the incident list into recurring failure patterns and "
            "extract a preventive lesson for each. Base everything on the incidents given."},
        {"role": "user", "content":
            'Return ONLY JSON: {"patterns": [{"theme": "...", "affected_assets": ["..."], '
            '"description": "...", "lesson": "...", "occurrences": N}]}\n\n'
            f"INCIDENTS:\n{listing}"},
    ]
    data = await complete_json(messages=messages, tier=Tier.SMART)
    patterns = data.get("patterns", []) if isinstance(data, dict) else []

    out: list[Pattern] = []
    for p in patterns:
        if not isinstance(p, dict):
            continue
        out.append(Pattern(
            theme=p.get("theme", ""),
            affected_assets=list(p.get("affected_assets", []) or []),
            description=p.get("description", ""),
            lesson=p.get("lesson", ""),
            occurrences=int(p.get("occurrences", 0) or 0),
        ))
    return out
