"""Copilot chat endpoints — grounded streaming answers with citations.

SSE protocol:
  data: {"meta": {citations, confidence, tags}}   ← first event
  data: {"delta": "..."}                            ← many
  data: {"done": true}                              ← last
Chat history is persisted to Postgres (sessions + chat_history).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.copilot import answer, stream_answer
from db.database import get_db
from db.models import ChatMessage, Session

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


async def _ensure_session(db: AsyncSession, session_id: str | None, first_msg: str) -> Session:
    if session_id:
        s = await db.get(Session, session_id)
        if s:
            return s
    s = Session(title=first_msg[:60])
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _history(db: AsyncSession, session_id: str) -> list[dict]:
    rows = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    )
    return [{"role": m.role, "content": m.content} for m in rows.scalars().all()]


@router.post("")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    session = await _ensure_session(db, req.session_id, req.message)
    history = await _history(db, session.id)

    # Compute retrieval + citations up front so we can emit them as the first event.
    setup = await answer(req.message, history)
    retrieval = setup.pop("_retrieval")

    # Persist the user turn now.
    db.add(ChatMessage(session_id=session.id, role="user", content=req.message))
    await db.commit()

    async def event_stream():
        meta = {"session_id": session.id, "citations": setup["citations"],
                "confidence": setup["confidence"], "tags": setup["tags"]}
        yield f"data: {json.dumps({'meta': meta})}\n\n"

        collected: list[str] = []
        async for delta in stream_answer(req.message, retrieval, history):
            collected.append(delta)
            yield f"data: {json.dumps({'delta': delta})}\n\n"

        # Persist the assistant turn with its citations.
        full = "".join(collected)
        async with get_db_context() as db2:
            db2.add(ChatMessage(
                session_id=session.id, role="assistant", content=full,
                citations={"citations": setup["citations"], "confidence": setup["confidence"]},
            ))
            await db2.commit()

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Separate context-managed session for use inside the stream generator (the
# request-scoped `db` is closed once the response starts streaming).
from contextlib import asynccontextmanager  # noqa: E402

from db.database import SessionLocal  # noqa: E402


@asynccontextmanager
async def get_db_context():
    async with SessionLocal() as session:
        yield session


@router.get("/history/{session_id}")
async def history(session_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    rows = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    )
    msgs = rows.scalars().all()
    return {
        "session_id": session_id,
        "messages": [
            {"role": m.role, "content": m.content, "citations": m.citations,
             "created_at": m.created_at.isoformat()}
            for m in msgs
        ],
    }
