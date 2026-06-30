"""Community detection and risk scoring over the fraud-network graph."""

import networkx as nx

# 10+ incidents on the same entity is the bar for a coordinated operation
# rather than an opportunistic one-off.
HIGH_RISK_INCIDENT_THRESHOLD = 10
MEDIUM_RISK_INCIDENT_THRESHOLD = 3


def _safe_float(value: float | int | str | None) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def detect_communities(graph: nx.Graph) -> list[set[str]]:
    if graph.number_of_edges() == 0:
        return [{node} for node in graph.nodes]
    return nx.community.louvain_communities(graph, weight="weight", seed=42)


def build_fraud_rings(
    graph: nx.Graph,
    communities: list[set[str]],
    incidents_by_id: dict[str, dict],
) -> list[dict]:
    rings: list[dict] = []
    for ring_id, members in enumerate(communities):
        if len(members) < 2:
            continue  # a single isolated entity is not a ring

        incident_ids: set[str] = set()
        for node in members:
            incident_ids.update(graph.nodes[node]["incident_ids"])

        by_type: dict[str, list[str]] = {
            t: []
            for t in ("mule_account", "phone_number", "victim_region", "scammer_id")
        }
        for node in members:
            by_type[graph.nodes[node]["type"]].append(graph.nodes[node]["value"])

        scam_types: set[str] = set()
        total_demanded = 0.0
        total_lost = 0.0
        for incident_id in incident_ids:
            incident = incidents_by_id.get(incident_id)
            if not incident:
                continue
            if incident.get("scam_type"):
                scam_types.add(incident["scam_type"])
            total_demanded += _safe_float(incident.get("amount_demanded"))
            total_lost += _safe_float(incident.get("amount_lost"))

        rings.append(
            {
                "ring_id": ring_id,
                "size": len(members),
                "incident_count": len(incident_ids),
                "mule_accounts": sorted(by_type["mule_account"]),
                "phone_numbers": sorted(by_type["phone_number"]),
                "victim_regions": sorted(by_type["victim_region"]),
                "scammer_ids": sorted(by_type["scammer_id"]),
                "scam_types": sorted(scam_types),
                "total_amount_demanded": total_demanded,
                "total_amount_lost": total_lost,
            }
        )

    rings.sort(key=lambda r: r["incident_count"], reverse=True)
    return rings


def _risk_level(incident_count: int) -> str:
    if incident_count >= HIGH_RISK_INCIDENT_THRESHOLD:
        return "high"
    if incident_count >= MEDIUM_RISK_INCIDENT_THRESHOLD:
        return "medium"
    return "low"


def ring_by_node(communities: list[set[str]]) -> dict[str, int]:
    return {
        node: ring_id for ring_id, members in enumerate(communities) for node in members
    }


def build_account_intelligence(
    graph: nx.Graph, ring_for_node: dict[str, int]
) -> list[dict]:
    intelligence: list[dict] = []
    for node, attrs in graph.nodes(data=True):
        incident_count = len(set(attrs["incident_ids"]))
        intelligence.append(
            {
                "node": node,
                "type": attrs["type"],
                "value": attrs["value"],
                "incident_count": incident_count,
                "risk_level": _risk_level(incident_count),
                "linked_entities": [
                    {
                        "node": n,
                        "type": graph.nodes[n]["type"],
                        "value": graph.nodes[n]["value"],
                    }
                    for n in graph.neighbors(node)
                ],
                "ring_id": ring_for_node.get(node),
            }
        )
    intelligence.sort(key=lambda a: a["incident_count"], reverse=True)
    return intelligence
