"""Complete fraud network intelligence pipeline, read-only against the
Neo4j graph already built by neo4j_run.py (does NOT re-push or clear
anything) plus the underlying MongoDB incident records for details Neo4j
doesn't store (scam_type, status, amount_lost, etc.).

Usage:
    python -m src.graph.neo4j_intelligence_run
"""

from __future__ import annotations

from pathlib import Path

from src.graph.analyze import detect_communities
from src.graph.court_reports import (
    write_evidence_package,
    write_fraud_rings_complete,
    write_inter_jurisdiction_alert,
    write_summary_statistics,
)
from src.graph.data import load_incidents
from src.graph.evidence_store import save_ring_intelligence, save_run_summary
from src.graph.neo4j_client import get_database, get_driver
from src.graph.neo4j_queries import (
    all_nodes,
    full_edge_list,
    high_degree_accounts,
    multi_region_accounts,
    rebuild_networkx_graph,
    shared_account_pairs,
)
from src.graph.ring_intelligence import CORE_OPERATOR_INCIDENT_THRESHOLD, build_ring_intelligence_packages

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "graph_neo4j"
EVIDENCE_DIR = OUTPUT_DIR / "court_evidence_packages"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    incidents = load_incidents()
    incidents_by_id = {i["incident_id"]: i for i in incidents if i.get("incident_id")}
    print(f"Loaded {len(incidents)} incidents from MongoDB.")

    driver = get_driver()
    database = get_database()
    try:
        driver.verify_connectivity()
        print("Connected to Neo4j Aura (read-only -- not modifying the graph).")

        # Query 2: core operators (5+ reuse)
        high_degree = high_degree_accounts(driver, database)
        core_operators = [r for r in high_degree if (r["incident_count"] or 0) >= CORE_OPERATOR_INCIDENT_THRESHOLD]
        print(f"Query 2 -- core operator accounts ({CORE_OPERATOR_INCIDENT_THRESHOLD}+ incidents): {len(core_operators)}")

        # Query 3: account-to-account linkage via shared phone (money-chain proxy --
        # we don't have literal inter-account transaction data, only shared
        # calling infrastructure, which is what this actually measures)
        chains = shared_account_pairs(driver, database)
        print(f"Query 3 -- linked account pairs (shared phone number): {len(chains)}")

        # Query 4: jurisdiction overlap
        multi_region = multi_region_accounts(driver, database)
        print(f"Query 4 -- accounts spanning multiple regions: {len(multi_region)}")

        # Query 1 + ring building: pull the graph back out, Louvain in NetworkX
        # (Aura free tier has no GDS plugin to run this inside Neo4j)
        edges = full_edge_list(driver, database)
        node_rows = all_nodes(driver, database)
    finally:
        driver.close()

    graph = rebuild_networkx_graph(edges)
    communities = detect_communities(graph)
    print(f"Query 1 -- communities detected (Louvain): {len(communities)}")

    rings = build_ring_intelligence_packages(graph, communities, incidents_by_id, node_rows)
    print(f"Built {len(rings)} fraud ring intelligence package(s) (2+ linked entities).")

    # MongoDB is the durable, access-controlled copy of the evidence itself
    # -- including the rendered report text, not just the structured data.
    # The local files below are disposable exports for quick reading built
    # from this exact same content; delete data/graph_neo4j/ anytime and
    # rerun this to get them back.
    save_ring_intelligence(rings)
    save_run_summary(rings, len(incidents))
    print(f"Persisted {len(rings)} ring(s) + run summary to MongoDB (fraud_rings, fraud_intelligence_runs).")

    write_fraud_rings_complete(OUTPUT_DIR / "fraud_rings_complete.json", rings)
    for ring in rings:
        write_evidence_package(EVIDENCE_DIR, ring)
    write_inter_jurisdiction_alert(OUTPUT_DIR / "inter_jurisdiction_alert.json", rings)
    write_summary_statistics(OUTPUT_DIR / "summary_statistics.txt", rings, len(incidents))

    print(f"\nLocal export copies written to {OUTPUT_DIR} (disposable, gitignored):")
    print("  - fraud_rings_complete.json")
    print(f"  - court_evidence_packages/  ({len(rings)} ring(s), 4 files each)")
    print("  - inter_jurisdiction_alert.json")
    print("  - summary_statistics.txt")


if __name__ == "__main__":
    main()
