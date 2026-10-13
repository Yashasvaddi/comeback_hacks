"""MinIO (S3-compatible) object storage for raw uploaded documents."""
from __future__ import annotations

import io
import uuid

from minio import Minio

from config import settings

_client: Minio | None = None


def get_minio() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def ensure_bucket() -> None:
    client = get_minio()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def put_object(filename: str, data: bytes, content_type: str) -> str:
    """Store bytes under a unique key. Returns the object key."""
    ensure_bucket()
    key = f"{uuid.uuid4()}/{filename}"
    get_minio().put_object(
        settings.minio_bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )
    return key


def get_object(key: str) -> bytes:
    resp = get_minio().get_object(settings.minio_bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()
