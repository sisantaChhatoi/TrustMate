"""Loads the fraud graph into Neo4j as Entity nodes + CO_OCCURS edges."""

import networkx as nx

from server.graph.neo4j_client import get_driver, get_neo4j_database

_RESET = "MATCH (n:Entity) DETACH DELETE n"

_UPSERT_NODE = """
MERGE (e:Entity {node_id: $node_id})
SET e.type = $type, e.value = $value,
    e.incident_count = $incident_count, e.risk_level = $risk_level,
    e.ring_id = $ring_id
"""

_UPSERT_EDGE = """
MATCH (a:Entity {node_id: $a}), (b:Entity {node_id: $b})
MERGE (a)-[r:CO_OCCURS]->(b)
SET r.weight = $weight
"""


def load_graph(graph: nx.Graph, account_intelligence: list[dict]) -> None:
    risk_by_node = {a["node"]: a for a in account_intelligence}
    driver = get_driver()
    db = get_neo4j_database()

    with driver.session(database=db) as session:
        session.run(_RESET)
        for node, attrs in graph.nodes(data=True):
            meta = risk_by_node.get(node, {})
            session.run(
                _UPSERT_NODE,
                node_id=node,
                type=attrs["type"],
                value=attrs["value"],
                incident_count=meta.get(
                    "incident_count", len(set(attrs["incident_ids"]))
                ),
                risk_level=meta.get("risk_level", "low"),
                ring_id=meta.get("ring_id"),
            )
        for a, b, data in graph.edges(data=True):
            session.run(_UPSERT_EDGE, a=a, b=b, weight=data["weight"])
