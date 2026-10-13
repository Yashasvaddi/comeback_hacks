"""Knowledge graph endpoints — nodes/edges for viz, asset subgraph, search, stats."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from graph.queries import (
    get_all_edges,
    get_all_nodes,
    get_asset_subgraph,
    graph_stats,
    search_entities,
)

router = APIRouter()


class GraphSearch(BaseModel):
    query: str


@router.get("/nodes")
async def nodes() -> dict:
    return {"nodes": await get_all_nodes()}


@router.get("/edges")
async def edges() -> dict:
    return {"edges": await get_all_edges()}


@router.get("/stats")
async def stats() -> dict:
    return await graph_stats()


@router.get("/asset/{tag}")
async def asset_subgraph(tag: str) -> dict:
    return await get_asset_subgraph(tag)


@router.post("/search")
async def search(body: GraphSearch) -> dict:
    return {"query": body.query, "results": await search_entities(body.query)}
