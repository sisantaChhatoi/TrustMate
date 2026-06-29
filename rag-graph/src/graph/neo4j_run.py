"""Builds and analyzes the fraud network graph using Neo4j Aura as the
graph store: pushes incidents from MongoDB, runs direct Cypher queries for
high-degree accounts / regional hotspots / shared-account pairs, then pulls
the edge list back to run Louvain ring detection in NetworkX (reusing
src/graph/analyze.py -- Aura's free tier has no Graph Data Science plugin
to run Louvain inside Neo4j itself).

Usage:
    python -m src.graph.neo4j_run
"""

from __future__ import annotations

import json
from pathlib import Path

from src.graph.analyze import build_account_intelligence, build_fraud_rings, detect_communities
from src.graph.data import load_incidents
from src.graph.neo4j_client import get_database, get_driver
from src.graph.neo4j_load import push_incidents
from src.graph.neo4j_queries import (
    full_edge_list,
    high_degree_accounts,
    rebuild_networkx_graph,
    regional_hotspots,
    shared_account_pairs,
)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "graph_neo4j"


def _clear_database(driver, database: str) -> None:
    with driver.session(database=database) as session:
        session.run("MATCH (n) DETACH DELETE n")


def _write_summary_report(
    path: Path,
    incident_count: int,
    high_degree: list[dict],
    hotspots: list[dict],
    shared_pairs: list[dict],
    rings: list[dict],
) -> None:
    lines = [
        "FRAUD NETWORK INTELLIGENCE SUMMARY (Neo4j Aura)",
        "=" * 50,
        f"Incidents analyzed: {incident_count}",
        f"Fraud rings detected (2+ linked entities): {len(rings)}",
        "",
        "HIGH-DEGREE MULE ACCOUNTS (Cypher: reused across most incidents)",
        "-" * 50,
    ]
    if high_degree:
        for row in high_degree[:10]:
            lines.append(
                f"  {row['account']} -- {row['incident_count']} incidents, "
                f"{row['distinct_phone_numbers']} distinct phone number(s)"
            )
    else:
        lines.append("  None yet.")
    lines.append("")

    lines.append("REGIONAL HOTSPOTS (Cypher: regions hit by most distinct numbers)")
    lines.append("-" * 50)
    if hotspots:
        for row in hotspots[:10]:
            lines.append(
                f"  {row['region']} -- {row['incident_count']} incidents, "
                f"{row['distinct_phone_numbers']} distinct phone number(s)"
            )
    else:
        lines.append("  None yet.")
    lines.append("")

    lines.append("LINKED ACCOUNT PAIRS (Cypher: accounts sharing a phone number)")
    lines.append("-" * 50)
    if shared_pairs:
        for row in shared_pairs[:10]:
            lines.append(f"  {row['account_1']} <-> {row['account_2']} via {row['shared_phone_number']}")
    else:
        lines.append("  None yet -- needs 2+ accounts sharing the same number.")
    lines.append("")

    lines.append("TOP FRAUD RINGS BY INCIDENT COUNT (Louvain, on data pulled from Neo4j)")
    lines.append("-" * 50)
    if not rings:
        lines.append("  None yet.")
    for ring in rings[:10]:
        lines.append(
            f"  Ring #{ring['ring_id']} -- {ring['incident_count']} incident(s), {ring['size']} linked entities, "
            f"scam types: {', '.join(ring['scam_types']) or 'unknown'}"
        )
        if ring["mule_accounts"]:
            lines.append(f"    Mule accounts: {', '.join(ring['mule_accounts'])}")
        if ring["phone_numbers"]:
            lines.append(f"    Phone numbers: {', '.join(ring['phone_numbers'])}")
        if ring["victim_regions"]:
            lines.append(f"    Victim regions: {', '.join(ring['victim_regions'])}")
        lines.append(
            f"    Total demanded: Rs {ring['total_amount_demanded']:,.0f}  |  "
            f"Total lost: Rs {ring['total_amount_lost']:,.0f}"
        )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    incidents = load_incidents()
    incidents_by_id = {i["incident_id"]: i for i in incidents if i.get("incident_id")}
    print(f"Loaded {len(incidents)} incidents from MongoDB.")

    driver = get_driver()
    database = get_database()
    try:
        driver.verify_connectivity()
        print("Connected to Neo4j Aura.")

        _clear_database(driver, database)
        push_incidents(driver, database, incidents)
        print("Pushed incidents to Neo4j.")

        high_degree = high_degree_accounts(driver, database)
        hotspots = regional_hotspots(driver, database)
        shared_pairs = shared_account_pairs(driver, database)
        edges = full_edge_list(driver, database)
    finally:
        driver.close()

    graph = rebuild_networkx_graph(edges)
    communities = detect_communities(graph)
    rings = build_fraud_rings(graph, communities, incidents_by_id)
    print(f"Detected {len(rings)} fraud ring(s) (2+ linked entities).")

    ring_by_node = {node: ring_id for ring_id, members in enumerate(communities) for node in members}
    intelligence = build_account_intelligence(graph, ring_by_node)

    (OUTPUT_DIR / "fraud_rings.json").write_text(json.dumps(rings, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUTPUT_DIR / "account_intelligence.json").write_text(
        json.dumps(
            {
                "entities": intelligence,
                "high_degree_accounts": high_degree,
                "regional_hotspots": hotspots,
                "shared_account_pairs": shared_pairs,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_summary_report(OUTPUT_DIR / "summary_report.txt", len(incidents), high_degree, hotspots, shared_pairs, rings)

    print(f"\nOutputs written to {OUTPUT_DIR}:")
    print("  - fraud_rings.json")
    print("  - account_intelligence.json")
    print("  - summary_report.txt")
    print("\nView the live graph interactively at https://console.neo4j.io (Query tab).")


if __name__ == "__main__":
    main()
