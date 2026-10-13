"""LLM entity + relationship extraction for the knowledge graph.

Runs on the FAST tier (gpt-oss:20b-cloud) since it's a high-frequency bulk op.
Results are cached by SHA256 of the input text so re-ingesting identical content
costs nothing (per the rate-limit strategy).
"""
from __future__ import annotations

import hashlib
import logging

from llm import Tier, complete_json

logger = logging.getLogger("ikb.entities")

# Process-local cache: sha256(text) -> extraction dict.
_cache: dict[str, dict] = {}

_SYSTEM = (
    "You are an information-extraction engine for industrial plant documents "
    "(maintenance reports, incident reports, inspection logs, safety procedures, "
    "compliance standards). Extract structured entities and relationships. "
    "Return ONLY JSON. Use exact identifiers from the text (e.g. equipment tags "
    "like P-101, V-200; regulation codes like OISD-STD-105). Omit fields you are "
    "unsure about rather than inventing them."
)

_SCHEMA_HINT = """Return a JSON object with these keys (each a list, possibly empty):

{
  "equipment":   [{"tag": "P-101", "name": "...", "type": "Pump|Valve|Vessel|Compressor|Exchanger|...", "location": "...", "manufacturer": "..."}],
  "persons":     [{"name": "...", "role": "engineer|operator|inspector|technician|..."}],
  "incidents":   [{"description": "...", "severity": "high|medium|low", "date": "YYYY-MM-DD or ''", "equipment_tag": "P-101"}],
  "regulations": [{"code": "OISD-STD-105", "name": "...", "authority": "OISD|PESO|Factory Act|..."}],
  "procedures":  [{"name": "...", "type": "startup|shutdown|maintenance|emergency|inspection"}],
  "locations":   [{"name": "Unit 3", "type": "plant|unit|area"}],
  "relationships": [
    {"source_type": "Equipment", "source_id": "P-101", "rel": "MAINTAINED_BY|LOCATED_AT|HAS_INCIDENT|REFERENCES_REGULATION|DESCRIBES_PROCEDURE", "target_type": "Person", "target_id": "..."}
  ]
}

Identifier rules: Equipment->tag, Person->name, Regulation->code, Location->name,
Procedure->name, Incident->description. Only include relationships where both
endpoints appear in the lists above."""


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_EMPTY = {
    "equipment": [], "persons": [], "incidents": [],
    "regulations": [], "procedures": [], "locations": [], "relationships": [],
}


async def extract_entities(text: str) -> dict:
    """Extract entities/relationships from a block of document text (cached)."""
    text = (text or "").strip()
    if not text:
        return {**_EMPTY}

    key = _hash(text)
    if key in _cache:
        return _cache[key]

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"{_SCHEMA_HINT}\n\n---\nDOCUMENT TEXT:\n{text[:8000]}"},
    ]
    try:
        result = await complete_json(messages=messages, tier=Tier.FAST)
    except Exception:
        logger.exception("Entity extraction failed; returning empty set")
        return {**_EMPTY}

    if not isinstance(result, dict):
        return {**_EMPTY}

    # Normalize: ensure all expected keys exist and are lists.
    normalized = {**_EMPTY}
    for k in normalized:
        v = result.get(k)
        if isinstance(v, list):
            normalized[k] = v

    _cache[key] = normalized
    return normalized
