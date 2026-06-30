"""Batch build of the fraud-intelligence layer: reads incidents from Mongo,
derives rings + per-entity risk + geospatial hotspots, writes snapshot docs
to the `intelligence` collection, and best-effort loads the graph into Neo4j.
Run via `python -m server.graph`."""

from datetime import datetime, timezone

from pymongo import MongoClient

from server.graph.analyze import (
    build_account_intelligence,
    build_fraud_rings,
    detect_communities,
    ring_by_node,
)
from server.graph.build import build_graph
from server.graph.deployment import build_deployment_strategy
from server.graph.geospatial import build_geojson, build_hotspots
from server.graph.ncrb_baseline import load_ncrb_baseline
from shared.config import settings

INTELLIGENCE_COLLECTION = "intelligence"


def _write_snapshot(col, kind: str, payload: dict) -> None:
    doc = {
        "_id": kind,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    col.replace_one({"_id": kind}, doc, upsert=True)


def run() -> dict:
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=10000)
    db = client[settings.mongodb_db]
    incidents = list(db["incidents"].find({}))
    incidents_by_id = {
        (inc.get("incident_id") or str(inc.get("_id"))): inc for inc in incidents
    }

    graph = build_graph(incidents)
    communities = detect_communities(graph)
    rings = build_fraud_rings(graph, communities, incidents_by_id)
    account_intelligence = build_account_intelligence(graph, ring_by_node(communities))

    hotspots, ungeocoded = build_hotspots(incidents)
    ncrb_baseline = load_ncrb_baseline()
    deployment_strategy = build_deployment_strategy(ncrb_baseline, hotspots)

    col = db[INTELLIGENCE_COLLECTION]
    _write_snapshot(col, "rings", {"rings": rings})
    _write_snapshot(col, "account_intelligence", {"accounts": account_intelligence})
    _write_snapshot(
        col,
        "geospatial",
        {
            "hotspots": hotspots,
            "geojson": build_geojson(hotspots),
            "deployment_strategy": deployment_strategy,
            "ungeocoded_count": ungeocoded,
        },
    )

    neo4j_loaded = False
    try:
        from server.graph.neo4j_load import load_graph

        load_graph(graph, account_intelligence)
        neo4j_loaded = True
    except Exception as exc:  # Neo4j is optional for the batch
        neo4j_error = str(exc)
    else:
        neo4j_error = None
    finally:
        client.close()

    return {
        "incidents": len(incidents),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "rings": len(rings),
        "hotspots": len(hotspots),
        "ungeocoded": ungeocoded,
        "neo4j_loaded": neo4j_loaded,
        "neo4j_error": neo4j_error,
    }
