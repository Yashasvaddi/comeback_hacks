"""Qdrant vector store: collection setup, upsert, and semantic search.

Stores one point per text chunk with payload {document_id, chunk_index, text,
doc_type, title}. Cosine distance over normalized MiniLM embeddings.
"""
from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config import settings
from vector_store.embeddings import EMBED_DIM, embed_text, embed_texts

_client: QdrantClient | None = None


def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def ensure_collection() -> None:
    client = get_qdrant()
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )


def upsert_chunks(document_id: str, chunks: list[dict]) -> int:
    """Embed and store chunks. Each chunk: {index, text, doc_type, title}."""
    if not chunks:
        return 0
    ensure_collection()
    vectors = embed_texts([c["text"] for c in chunks])
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "document_id": document_id,
                "chunk_index": c["index"],
                "text": c["text"],
                "doc_type": c.get("doc_type", "unknown"),
                "title": c.get("title", ""),
            },
        )
        for c, vec in zip(chunks, vectors)
    ]
    get_qdrant().upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


def search(query: str, top_k: int = 6, doc_type: str | None = None) -> list[dict]:
    """Semantic search → list of {text, document_id, chunk_index, score, ...}."""
    ensure_collection()
    qvec = embed_text(query)
    flt = None
    if doc_type:
        flt = Filter(
            must=[FieldCondition(key="doc_type", match=MatchValue(value=doc_type))]
        )
    hits = get_qdrant().search(
        collection_name=settings.qdrant_collection,
        query_vector=qvec,
        limit=top_k,
        query_filter=flt,
    )
    return [{**h.payload, "score": h.score} for h in hits]
