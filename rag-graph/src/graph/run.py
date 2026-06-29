"""Builds and analyzes the fraud network graph from MongoDB incidents.

Usage:
    python -m src.graph.run
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from src.graph.analyze import build_account_intelligence, build_fraud_rings, detect_communities
from src.graph.build import build_graph
from src.graph.data import load_incidents
from src.graph.report import write_summary_report

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "graph"


def _graphml_safe(graph: nx.Graph) -> nx.Graph:
    """GraphML attributes must be primitives -- the list-valued
    incident_ids attribute is joined into a string for this export only;
    the JSON outputs keep the real lists."""
    export_graph = graph.copy()
    for _, attrs in export_graph.nodes(data=True):
        attrs["incident_ids"] = ",".join(attrs["incident_ids"])
    for _, _, attrs in export_graph.edges(data=True):
        attrs["incident_ids"] = ",".join(attrs["incident_ids"])
    return export_graph


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    incidents = load_incidents()
    incidents_by_id = {i["incident_id"]: i for i in incidents if i.get("incident_id")}
    print(f"Loaded {len(incidents)} incidents from MongoDB.")

    graph = build_graph(incidents)
    print(f"Built graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges.")

    communities = detect_communities(graph)
    rings = build_fraud_rings(graph, communities, incidents_by_id)
    print(f"Detected {len(rings)} fraud ring(s) (2+ linked entities).")

    ring_by_node: dict[str, int] = {}
    for ring_id, members in enumerate(communities):
        for node in members:
            ring_by_node[node] = ring_id

    intelligence = build_account_intelligence(graph, ring_by_node)

    nx.write_graphml(_graphml_safe(graph), OUTPUT_DIR / "network_graph.graphml")
    (OUTPUT_DIR / "fraud_rings.json").write_text(json.dumps(rings, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUTPUT_DIR / "account_intelligence.json").write_text(
        json.dumps(intelligence, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_summary_report(OUTPUT_DIR / "summary_report.txt", graph, rings, intelligence, len(incidents))

    print(f"\nOutputs written to {OUTPUT_DIR}:")
    print("  - network_graph.graphml")
    print("  - fraud_rings.json")
    print("  - account_intelligence.json")
    print("  - summary_report.txt")


if __name__ == "__main__":
    main()
