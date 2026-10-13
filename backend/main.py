"""FastAPI entry point for the Industrial Knowledge Intelligence platform."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.database import init_db
from graph.neo4j_client import close_driver, init_schema
from routers import chat, compliance, graph, ingest, lessons, rca, stream_frontend, data_stream, voice_router, whatsapp, incident_call

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ikb")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing database schema")
    await init_db()
    try:
        await init_schema()
        logger.info("Neo4j schema ready")
    except Exception:
        logger.exception("Neo4j schema init failed (graph features degraded)")
    logger.info("Database ready")
    yield
    await close_driver()
    logger.info("Shutting down")


app = FastAPI(
    title="Industrial Knowledge Intelligence API",
    version="0.1.0",
    description="Document ingestion, knowledge graph, and multi-agent copilot for industrial operations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(rca.router, prefix="/api/rca", tags=["rca"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["compliance"])
app.include_router(lessons.router, prefix="/api/lessons", tags=["lessons"])
app.include_router(data_stream.router)
app.include_router(stream_frontend.router)
app.include_router(voice_router.router)
app.include_router(incident_call.router, prefix="/api")
app.include_router(whatsapp.router, prefix="/api")

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "llm_fast": settings.llm_model_fast,
        "llm_smart": settings.llm_model_smart,
        "llm_provider": settings.ollama_base_url,
    }
