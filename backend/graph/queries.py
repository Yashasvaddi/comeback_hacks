"""Read queries over the knowledge graph for the API and agents."""
from __future__ import annotations

from graph.neo4j_client import run_read


def display_key(props: dict) -> str:
    """Human-readable label for a node across all types.

    Order matters: equipment tag → person/location name → regulation code →
    document title → procedure title → incident description. Long descriptions
    are truncated so graph labels stay readable.
    """
    key = (
        props.get("tag")
        or props.get("name")
        or props.get("code")
        or props.get("title")
        or props.get("description")
        or props.get("id", "")
    )
    key = str(key)
    return key if len(key) <= 48 else key[:45] + "…"


async def get_all_nodes(limit: int = 300) -> list[dict]:
    rows = await run_read(
        "MATCH (n) RETURN labels(n)[0] AS label, n AS props, elementId(n) AS id "
        "LIMIT $limit",
        limit=limit,
    )
    nodes = []
    for r in rows:
        props = dict(r["props"])
        nodes.append({"id": r["id"], "label": r["label"], "key": display_key(props), "props": props})
    return nodes


async def get_all_edges(limit: int = 600) -> list[dict]:
    rows = await run_read(
        "MATCH (a)-[r]->(b) "
        "RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS rel "
        "LIMIT $limit",
        limit=limit,
    )
    return [{"source": r["source"], "target": r["target"], "rel": r["rel"]} for r in rows]


async def get_asset_subgraph(tag: str) -> dict:
    """Everything within 1-2 hops of an equipment tag."""
    rows = await run_read(
        "MATCH (e:Equipment {tag: $tag}) "
        "OPTIONAL MATCH (e)-[r]-(n) "
        "RETURN e AS equipment, collect(DISTINCT {rel: type(r), node: n, label: labels(n)[0]}) AS neighbors",
        tag=tag,
    )
    if not rows:
        return {"tag": tag, "found": False, "equipment": None, "neighbors": []}
    row = rows[0]
    neighbors = []
    for nb in row["neighbors"]:
        if nb.get("node") is None:
            continue
        props = dict(nb["node"])
        neighbors.append({
            "rel": nb["rel"],
            "label": nb["label"],
            "key": display_key(props),
            "props": props,
        })
    return {
        "tag": tag,
        "found": True,
        "equipment": dict(row["equipment"]) if row["equipment"] else None,
        "neighbors": neighbors,
    }


async def search_entities(query: str, limit: int = 20) -> list[dict]:
    """Case-insensitive substring search across common name fields."""
    rows = await run_read(
        "MATCH (n) "
        "WHERE toLower(coalesce(n.tag,'')) CONTAINS toLower($q) "
        "   OR toLower(coalesce(n.name,'')) CONTAINS toLower($q) "
        "   OR toLower(coalesce(n.code,'')) CONTAINS toLower($q) "
        "   OR toLower(coalesce(n.description,'')) CONTAINS toLower($q) "
        "RETURN labels(n)[0] AS label, n AS props LIMIT $limit",
        q=query, limit=limit,
    )
    out = []
    for r in rows:
        props = dict(r["props"])
        out.append({"label": r["label"], "key": display_key(props), "props": props})
    return out


async def graph_stats() -> dict:
    rows = await run_read(
        "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS c ORDER BY c DESC"
    )
    rels = await run_read("MATCH ()-[r]->() RETURN count(r) AS c")
    return {
        "node_counts": {r["label"]: r["c"] for r in rows},
        "total_relationships": rels[0]["c"] if rels else 0,
    }
