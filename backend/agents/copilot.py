"""Expert Knowledge Copilot — grounded, streaming, cited answers.

Retrieves hybrid context (Qdrant + Neo4j), grounds gpt-oss:120b-cloud on it,
and streams the answer. Citations come from the retrieved chunks; a confidence
score is derived from retrieval strength.
"""
from __future__ import annotations

from typing import AsyncIterator

from agents.retriever import build_context_block, retrieve
from llm import Tier, stream

_SYSTEM = (
    "You are the Expert Knowledge Copilot for an industrial plant. Answer the "
    "engineer's question using ONLY the provided context (document excerpts and "
    "knowledge-graph relationships). Cite sources inline as [1], [2] matching the "
    "numbered excerpts. If the context is insufficient, say so plainly — never "
    "fabricate equipment details, dates, or readings. Be concise and operational."
)


def _confidence(retrieval: dict) -> float:
    """Heuristic confidence from top semantic score + graph corroboration."""
    chunks = retrieval.get("chunks", [])
    if not chunks:
        return 0.0
    top = float(chunks[0].get("score", 0.0))
    graph_bonus = 0.1 if retrieval.get("graph_context") else 0.0
    return round(min(1.0, top + graph_bonus), 2)


async def answer(query: str, history: list[dict] | None = None) -> dict:
    """Non-streaming entry — returns retrieval + citations + confidence for setup.

    Used by the chat router to attach metadata; the text itself is streamed via
    `stream_answer`.
    """
    retrieval = await retrieve(query)
    return {
        "citations": retrieval["citations"],
        "confidence": _confidence(retrieval),
        "tags": retrieval["tags"],
        "_retrieval": retrieval,
    }


async def stream_answer(
    query: str, retrieval: dict, history: list[dict] | None = None
) -> AsyncIterator[str]:
    """Stream the grounded answer text for an already-computed retrieval."""
    context = build_context_block(retrieval)
    messages = [{"role": "system", "content": _SYSTEM}]
    for h in (history or [])[-6:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append(
        {"role": "user", "content": f"CONTEXT:\n{context}\n\n---\nQUESTION: {query}"}
    )
    async for delta in stream(messages=messages, tier=Tier.SMART):
        yield delta
