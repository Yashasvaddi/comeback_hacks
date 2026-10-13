"""Ingestion endpoints: upload documents and poll job status.

Upload → store raw bytes in MinIO, create document + job rows, kick off the
ingestion pipeline (parse/chunk/embed/index) as a background task.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.crud import create_document, create_job, get_job, list_documents
from db.database import get_db
from parsers.base import UnsupportedFormat, _EXT_DISPATCH
from services.ingestion import run_ingestion
from storage.minio_client import put_object

import os

router = APIRouter()


@router.post("/upload")
async def upload(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Accept one or more documents and start ingestion for each."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    results: list[dict] = []

    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in _EXT_DISPATCH:
            results.append({"filename": f.filename, "status": "rejected", "reason": f"unsupported type {ext}"})
            continue

        data = await f.read()
        if len(data) > max_bytes:
            results.append({"filename": f.filename, "status": "rejected", "reason": "too large"})
            continue

        key = put_object(f.filename, data, f.content_type or "application/octet-stream")
        title = os.path.splitext(os.path.basename(f.filename))[0]
        doc = await create_document(
            db,
            title=title,
            filename=f.filename,
            content_type=f.content_type or "application/octet-stream",
            minio_key=key,
            size_bytes=len(data),
        )
        job = await create_job(db, document_id=doc.id)
        background.add_task(run_ingestion, job.id, doc.id, f.filename, data, title)
        results.append({"filename": f.filename, "status": "accepted", "document_id": doc.id, "job_id": job.id})

    return {"results": results}


@router.get("/status/{job_id}")
async def job_status(job_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    job = await get_job(db, job_id)
    if job is None:
        return {"job_id": job_id, "status": "not_found"}
    return {
        "job_id": job.id,
        "document_id": job.document_id,
        "status": job.status,
        "stage": job.stage,
        "progress": job.progress,
        "error": job.error,
    }


@router.get("/documents")
async def documents(db: AsyncSession = Depends(get_db)) -> dict:
    docs = await list_documents(db)
    return {
        "total": len(docs),
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "filename": d.filename,
                "doc_type": d.doc_type,
                "chunk_count": d.chunk_count,
                "size_bytes": d.size_bytes,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ],
    }
