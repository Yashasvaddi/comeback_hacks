"""Hybrid retrieval: Qdrant semantic search + Neo4j graph context.

For a user query we:
  1. Pull the top-k semantically similar chunks from Qdrant (the "what was
     written" evidence, each a citation).
  2. Detect equipment tags / entities in the query and pull their graph
     neighborhoods from Neo4j (the "how things connect" context).
  3. Assemble a single context bundle the LLM can ground its answer in.
"""
from __future__ import annotations

import re

from graph.queries import get_asset_subgraph, search_entities
from vector_store.qdrant_store import search as vector_search

# Industrial tag pattern, e.g. P-101, V-200, E-301, C-150.
_TAG_RE = re.compile(r"\b([A-Z]{1,3}-\d{2,4})\b")


async def detect_entities(query: str) -> list[str]:
    """Find equipment tags explicitly in the query, plus fuzzy graph matches."""
    tags = set(_TAG_RE.findall(query.upper()))
    if not tags:
        # Fall back to a graph name search on salient words (len > 3).
        for word in {w for w in re.findall(r"[A-Za-z]{4,}", query)}:
            hits = await search_entities(word, limit=3)
            for h in hits:
                if h["label"] == "Equipment":
                    tags.add(h["key"])
    return list(tags)


async def retrieve(query: str, top_k: int = 6) -> dict:
    """Return {chunks, graph_context, citations} for a query."""
    chunks = vector_search(query, top_k=top_k)

    tags = await detect_entities(query)
    graph_context: list[dict] = []
    for tag in tags[:3]:
        sg = await get_asset_subgraph(tag)
        if sg.get("found"):
            graph_context.append(sg)

    citations = [
        {
            "document_id": c.get("document_id"),
            "title": c.get("title", ""),
            "chunk_index": c.get("chunk_index"),
            "score": round(float(c.get("score", 0.0)), 3),
        }
        for c in chunks
    ]
    return {"chunks": chunks, "graph_context": graph_context, "citations": citations, "tags": tags}


def build_context_block(retrieval: dict) -> str:
    """Render retrieved evidence into a prompt-ready context string."""
    parts: list[str] = []

    if retrieval["chunks"]:
        parts.append("=== DOCUMENT EXCERPTS ===")
        for i, c in enumerate(retrieval["chunks"], 1):
            title = c.get("title") or c.get("document_id", "")[:8]
            parts.append(f"[{i}] (source: {title}, relevance {c.get('score', 0):.2f})\n{c.get('text','')}")

    for sg in retrieval["graph_context"]:
        eq = sg.get("equipment") or {}
        parts.append(
            f"\n=== KNOWLEDGE GRAPH: {sg['tag']} ===\n"
            f"Equipment: {eq.get('name', sg['tag'])} (type {eq.get('type','?')}, "
            f"location {eq.get('location','?')})"
        )
        for nb in sg.get("neighbors", []):
            parts.append(f"  - {nb['rel']} → ({nb['label']}) {nb['key']}")

    return "\n".join(parts) if parts else "(no relevant context found)"
