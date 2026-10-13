"""Build knowledge-graph nodes/edges from extracted entities.

Everything is MERGE-based on natural keys, so:
  * re-ingesting a document is idempotent, and
  * the same entity mentioned in multiple documents (e.g. pump P-101) becomes a
    single shared node — this is the cross-document linking (P3.4). Each entity
    is linked to the Document it was found in via :MENTIONS / :REFERENCED_IN.
"""
from __future__ import annotations

import logging

from graph.neo4j_client import run_write

logger = logging.getLogger("ikb.graph")

# Map an entity-type name to (label, natural-key field).
_NODE_KEYS = {
    "Equipment": "tag",
    "Person": "name",
    "Regulation": "code",
    "Location": "name",
    "Procedure": "name",
    "Incident": "description",
    "Document": "id",
}

# Allowed relationship verbs (avoid Cypher injection via the rel type).
_ALLOWED_RELS = {
    "MAINTAINED_BY", "LOCATED_AT", "HAS_INCIDENT", "REFERENCES_REGULATION",
    "DESCRIBES_PROCEDURE", "CAUSED_BY", "INVESTIGATED_BY", "AUTHORED",
    "REQUIRED_BY", "SIMILAR_TO",
}


async def upsert_document_node(doc_id: str, title: str, doc_type: str, date: str = "") -> None:
    await run_write(
        "MERGE (d:Document {id: $id}) "
        "SET d.title = $title, d.type = $doc_type, d.date = $date",
        id=doc_id, title=title, doc_type=doc_type, date=date,
    )


async def _merge_node(label: str, key_field: str, key_value: str, props: dict) -> None:
    # Drop empties so we don't overwrite good values with blanks.
    clean = {k: v for k, v in props.items() if v not in (None, "", []) and k != key_field}
    await run_write(
        f"MERGE (n:{label} {{{key_field}: $key}}) "
        f"SET n += $props",
        key=key_value, props=clean,
    )


async def _link_to_document(label: str, key_field: str, key_value: str, doc_id: str) -> None:
    await run_write(
        f"MATCH (n:{label} {{{key_field}: $key}}), (d:Document {{id: $doc_id}}) "
        f"MERGE (n)-[:REFERENCED_IN]->(d)",
        key=key_value, doc_id=doc_id,
    )


async def build_graph(doc_id: str, title: str, doc_type: str, entities: dict) -> dict:
    """Create nodes + relationships from an extraction dict. Returns counts."""
    counts = {"nodes": 0, "rels": 0}

    await upsert_document_node(doc_id, title, doc_type)

    # ── Nodes ──
    type_map = [
        ("Equipment", "equipment", "tag"),
        ("Person", "persons", "name"),
        ("Regulation", "regulations", "code"),
        ("Location", "locations", "name"),
        ("Procedure", "procedures", "name"),
    ]
    for label, list_key, key_field in type_map:
        for item in entities.get(list_key, []):
            kv = (item.get(key_field) or "").strip()
            if not kv:
                continue
            await _merge_node(label, key_field, kv, item)
            await _link_to_document(label, key_field, kv, doc_id)
            counts["nodes"] += 1

    # Incidents (keyed by description; also link to their equipment if given).
    for inc in entities.get("incidents", []):
        desc = (inc.get("description") or "").strip()
        if not desc:
            continue
        await _merge_node("Incident", "description", desc,
                          {"severity": inc.get("severity", ""), "date": inc.get("date", "")})
        await _link_to_document("Incident", "description", desc, doc_id)
        counts["nodes"] += 1
        eq = (inc.get("equipment_tag") or "").strip()
        if eq:
            await run_write(
                "MATCH (e:Equipment {tag: $tag}), (i:Incident {description: $desc}) "
                "MERGE (e)-[:HAS_INCIDENT]->(i)",
                tag=eq, desc=desc,
            )
            counts["rels"] += 1

    # ── Explicit relationships ──
    for rel in entities.get("relationships", []):
        verb = (rel.get("rel") or "").strip().upper()
        st, si = rel.get("source_type"), (rel.get("source_id") or "").strip()
        tt, ti = rel.get("target_type"), (rel.get("target_id") or "").strip()
        if verb not in _ALLOWED_RELS or not all([st, si, tt, ti]):
            continue
        sk, tk = _NODE_KEYS.get(st), _NODE_KEYS.get(tt)
        if not sk or not tk:
            continue
        await run_write(
            f"MATCH (a:{st} {{{sk}: $si}}), (b:{tt} {{{tk}: $ti}}) "
            f"MERGE (a)-[:{verb}]->(b)",
            si=si, ti=ti,
        )
        counts["rels"] += 1

    logger.info("Graph built for doc %s: %d nodes, %d rels", doc_id, counts["nodes"], counts["rels"])
    return counts
