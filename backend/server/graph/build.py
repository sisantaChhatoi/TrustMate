"""Co-occurrence graph over incidents: each incident is a clique of its
entities, so an entity reused across incidents becomes a high-degree node."""

from itertools import combinations

import networkx as nx

# graph node type -> Incident field
NODE_FIELDS = {
    "mule_account": "mule_account",
    "phone_number": "caller_number",
    "victim_region": "victim_region",
    "scammer_id": "mule_upi",
}


def _node_id(node_type: str, value: str) -> str:
    return f"{node_type}:{value}"


def _normalize(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def build_graph(incidents: list[dict]) -> nx.Graph:
    graph = nx.Graph()

    for incident in incidents:
        incident_id = incident.get("incident_id") or str(incident.get("_id"))
        nodes_in_incident: list[str] = []

        for node_type, field in NODE_FIELDS.items():
            value = _normalize(incident.get(field))
            if value is None:
                continue
            node_id = _node_id(node_type, value)
            nodes_in_incident.append(node_id)

            if graph.has_node(node_id):
                graph.nodes[node_id]["incident_ids"].append(incident_id)
            else:
                graph.add_node(
                    node_id,
                    type=node_type,
                    value=value,
                    incident_ids=[incident_id],
                )

        for a, b in combinations(sorted(nodes_in_incident), 2):
            if graph.has_edge(a, b):
                graph[a][b]["weight"] += 1
                graph[a][b]["incident_ids"].append(incident_id)
            else:
                graph.add_edge(a, b, weight=1, incident_ids=[incident_id])

    return graph
