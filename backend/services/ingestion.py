"""Ingestion pipeline (Phase 2 data layer).

Orchestrates: parse → chunk → embed → Qdrant, updating the job record at each
stage. Graph entity extraction (Neo4j) is layered on in Phase 3 as an extra
stage at the end of this same flow.

Runs as a FastAPI background task with its own DB session (the request session
is already closed by the time this executes).
"""
from __future__ import annotations

import logging

from db.crud import finalize_document, update_job
from db.database import SessionLocal
from graph.entity_extraction import extract_entities
from graph.graph_builder import build_graph
from parsers.base import parse_document
from utils.chunker import chunk_text
from vector_store.qdrant_store import upsert_chunks

logger = logging.getLogger("ikb.ingestion")


async def run_ingestion(job_id: str, document_id: str, filename: str, data: bytes, title: str) -> None:
    """Full ingestion for one document. Best-effort; records errors on the job."""
    async with SessionLocal() as db:
        try:
            await update_job(db, job_id, status="running", stage="parsing", progress=10)
            parsed = parse_document(filename, data)

            if not parsed.text.strip():
                await update_job(
                    db, job_id, status="failed", stage="parsing",
                    error="No text could be extracted from the document.",
                )
                return

            await update_job(db, job_id, stage="chunking", progress=40)
            chunks = chunk_text(parsed.text)
            chunk_payload = [
                {
                    "index": c.index,
                    "text": c.text,
                    "doc_type": parsed.doc_type,
                    "title": title,
                }
                for c in chunks
            ]

            await update_job(db, job_id, stage="embedding", progress=55)
            stored = upsert_chunks(document_id, chunk_payload)

            # ── Knowledge graph stage: extract entities → build graph ──
            await update_job(db, job_id, stage="graph", progress=75)
            try:
                entities = await extract_entities(parsed.text)
                await build_graph(document_id, title, parsed.doc_type, entities)
            except Exception:
                # Graph build is best-effort — a failure here shouldn't fail the
                # whole ingestion (chunks are already searchable in Qdrant).
                logger.exception("Graph build failed for %s (continuing)", filename)

            await update_job(db, job_id, stage="indexing", progress=90)
            await finalize_document(
                db,
                document_id,
                doc_type=parsed.doc_type,
                chunk_count=stored,
                summary=parsed.text[:500],
            )

            await update_job(db, job_id, status="complete", stage="done", progress=100)
            logger.info("Ingested %s: %d chunks (%s)", filename, stored, parsed.doc_type)
        except Exception as e:  # noqa: BLE001
            logger.exception("Ingestion failed for %s", filename)
            await update_job(db, job_id, status="failed", error=str(e))
