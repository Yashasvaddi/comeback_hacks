"""Async Neo4j client: driver lifecycle, schema constraints, query helpers.

A single shared AsyncDriver is created lazily. `init_schema()` creates uniqueness
constraints (which also back lookups during MERGE) for each node type's natural
key, so re-ingesting a document doesn't duplicate equipment/persons/etc.
"""
from __future__ import annotations

from neo4j import AsyncDriver, AsyncGraphDatabase

from config import settings

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


# Natural keys used for MERGE de-duplication.
_CONSTRAINTS = [
    ("Equipment", "tag"),
    ("Document", "id"),
    ("Incident", "id"),
    ("Person", "name"),
    ("Regulation", "code"),
    ("Procedure", "id"),
    ("Location", "name"),
]


async def init_schema() -> None:
    """Create uniqueness constraints if missing. Idempotent."""
    driver = get_driver()
    async with driver.session() as session:
        for label, key in _CONSTRAINTS:
            await session.run(
                f"CREATE CONSTRAINT {label.lower()}_{key}_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
            )


async def run_write(query: str, **params) -> None:
    driver = get_driver()
    async with driver.session() as session:
        await session.run(query, **params)


async def run_read(query: str, **params) -> list[dict]:
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(query, **params)
        return [record.data() async for record in result]
