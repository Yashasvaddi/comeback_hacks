"""Async CRUD helpers for documents and jobs."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Document, Job


async def create_document(
    db: AsyncSession,
    *,
    title: str,
    filename: str,
    content_type: str,
    minio_key: str,
    size_bytes: int,
    doc_type: str = "unknown",
) -> Document:
    doc = Document(
        title=title,
        filename=filename,
        content_type=content_type,
        minio_key=minio_key,
        size_bytes=size_bytes,
        doc_type=doc_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def create_job(db: AsyncSession, *, document_id: str, kind: str = "ingestion") -> Job:
    job = Job(document_id=document_id, kind=kind, status="pending")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def update_job(
    db: AsyncSession,
    job_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress: int | None = None,
    error: str | None = None,
) -> None:
    job = await db.get(Job, job_id)
    if job is None:
        return
    if status is not None:
        job.status = status
    if stage is not None:
        job.stage = stage
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error = error
    await db.commit()


async def finalize_document(
    db: AsyncSession,
    document_id: str,
    *,
    doc_type: str,
    chunk_count: int,
    summary: str | None = None,
) -> None:
    doc = await db.get(Document, document_id)
    if doc is None:
        return
    doc.doc_type = doc_type
    doc.chunk_count = chunk_count
    if summary is not None:
        doc.summary = summary
    await db.commit()


async def get_job(db: AsyncSession, job_id: str) -> Job | None:
    return await db.get(Job, job_id)


async def list_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return list(result.scalars().all())
