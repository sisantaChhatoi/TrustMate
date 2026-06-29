"""Builds full fraud-ring intelligence packages from the Neo4j graph plus
the underlying MongoDB incident records.

Every number in here is computed from real incident data already collected
through the chat -- nothing is invented or estimated to "look realistic."
Where the underlying data doesn't exist (e.g. we never capture a victim's
name/identity -- only an anonymous session_id, which is intentional), the
field says so explicitly rather than being silently omitted or faked.

confidence_score is a transparent, documented heuristic (see
_confidence_score), not a black-box number -- this matters if these
packages are ever actually shown to an investigator: a number with no
stated method behind it isn't evidence, it's a guess wearing a costume.
"""

from __future__ import annotations

from collections import Counter

from src.graph.jurisdiction import map_region_to_jurisdiction

CORE_OPERATOR_INCIDENT_THRESHOLD = 5  # "reused 5+ times" per the brief


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ring_type(scam_types: list[str]) -> str:
    if not scam_types:
        return "unknown"
    counts = Counter(scam_types)
    top_type, top_count = counts.most_common(1)[0]
    tied = [t for t, c in counts.items() if c == top_count]
    return top_type if len(tied) == 1 else "mixed"


def _confidence_score(incident_count: int, scam_types: list[str]) -> dict:
    """Two transparent components:
    - incident_volume (up to 0.7): more linked incidents = stronger signal
      this is a real recurring operation rather than coincidence. Scales
      linearly, capped at 10 incidents.
    - type_consistency (up to 0.3): every incident in the ring sharing one
      scam_type is a coherence signal; a mix of unrelated types suggests
      the clustering might just be two unrelated scammers who happened to
      reuse the same number, not one operation.
    Returned with the formula's inputs alongside the score, so the number
    is auditable rather than asserted."""
    incident_volume = min(1.0, incident_count / 10) * 0.7
    distinct_types = len(set(scam_types)) or 1
    type_consistency = 0.3 if distinct_types == 1 else round(0.3 / distinct_types, 3)
    return {
        "score": round(incident_volume + type_consistency, 2),
        "method": "0.7 * min(1, incident_count/10) + 0.3 if all linked incidents share one scam_type, else 0.3/distinct_scam_types",
        "incident_count": incident_count,
        "distinct_scam_types": distinct_types,
    }


def _format_inr(amount: float) -> str:
    if amount >= 1_00_00_000:
        return f"Rs {amount / 1_00_00_000:.2f} crore"
    if amount >= 1_00_000:
        return f"Rs {amount / 1_00_000:.2f} lakh"
    return f"Rs {amount:,.0f}"


def _node_meta(all_node_rows: list[dict]) -> dict[str, dict]:
    from src.graph.neo4j_queries import TYPE_MAP

    meta = {}
    for row in all_node_rows:
        node_type = TYPE_MAP.get(row["node_type"], row["node_type"])
        node_id = f"{node_type}:{row['value']}"
        meta[node_id] = row
    return meta


def build_ring_intelligence_packages(
    graph, communities: list[set[str]], incidents_by_id: dict[str, dict], all_node_rows: list[dict]
) -> list[dict]:
    node_meta = _node_meta(all_node_rows)
    packages = []

    for ring_index, members in enumerate(communities):
        if len(members) < 2:
            continue

        incident_ids: set[str] = set()
        for node in members:
            incident_ids.update(graph.nodes[node]["incident_ids"])
        if not incident_ids:
            continue

        ring_incidents = [incidents_by_id[i] for i in incident_ids if i in incidents_by_id]
        scam_types = [inc.get("scam_type") for inc in ring_incidents if inc.get("scam_type")]
        timestamps = sorted(inc.get("timestamp") for inc in ring_incidents if inc.get("timestamp"))
        regions = sorted({inc.get("victim_region") for inc in ring_incidents if inc.get("victim_region")})
        jurisdictions = sorted({map_region_to_jurisdiction(r) for r in regions})

        total_demanded = sum(_safe_float(inc.get("amount_demanded")) or 0.0 for inc in ring_incidents)
        total_lost = sum(_safe_float(inc.get("amount_lost")) or 0.0 for inc in ring_incidents)

        core_members = []
        mule_account_network: dict[str, list[str]] = {}
        phone_call_network: dict[str, list[str]] = {}

        for node in members:
            attrs = graph.nodes[node]
            node_incident_ids = set(attrs["incident_ids"])
            node_incidents = [incidents_by_id[i] for i in node_incident_ids if i in incidents_by_id]
            meta = node_meta.get(node, {})
            neighbor_values = [graph.nodes[n]["value"] for n in graph.neighbors(node)]

            if attrs["type"] == "mule_account":
                core_members.append(
                    {
                        "mule_account": attrs["value"],
                        "incident_count": len(node_incident_ids),
                        "total_amount_requested": sum(
                            _safe_float(inc.get("amount_demanded")) or 0.0 for inc in node_incidents
                        ),
                        "is_core_operator": len(node_incident_ids) >= CORE_OPERATOR_INCIDENT_THRESHOLD,
                    }
                )
                mule_account_network[attrs["value"]] = neighbor_values
            elif attrs["type"] == "phone_number":
                core_members.append(
                    {
                        "phone_number": attrs["value"],
                        # "calls_made" is approximated as incidents linked to this
                        # number -- we don't have raw call-log data, only one
                        # recorded conversation per incident.
                        "calls_made": len(node_incident_ids),
                        "regions_targeted": sorted({inc.get("victim_region") for inc in node_incidents if inc.get("victim_region")}),
                    }
                )
                phone_call_network[attrs["value"]] = neighbor_values
            elif attrs["type"] == "scammer_id":
                core_members.append(
                    {
                        "scammer_id": attrs["value"],
                        "incident_count": len(node_incident_ids),
                        "operational_since": meta.get("first_seen"),
                    }
                )
            # victim_region nodes are summarized under jurisdictions_affected, not core_members

        incident_timeline = sorted(
            (
                {
                    "incident_id": inc.get("incident_id"),
                    "timestamp": inc.get("timestamp"),
                    "scam_type": inc.get("scam_type"),
                    "status": inc.get("status"),
                }
                for inc in ring_incidents
            ),
            key=lambda x: x["timestamp"] or "",
        )

        evidence_chain = sorted(
            (
                {
                    "incident_id": inc.get("incident_id"),
                    "victim_session_ref": inc.get("session_id"),  # no victim identity is ever captured -- by design
                    "region": inc.get("victim_region"),
                    "incident_timestamp": inc.get("timestamp"),
                    "mule_account_used": inc.get("mule_account"),
                    "phone_used": inc.get("caller_number"),
                    "scammer_upi_used": inc.get("mule_upi"),
                    "amount_requested": _safe_float(inc.get("amount_demanded")),
                    "amount_lost": _safe_float(inc.get("amount_lost")),
                    "status": inc.get("status"),
                }
                for inc in ring_incidents
            ),
            key=lambda x: x["incident_timestamp"] or "",
        )

        confidence = _confidence_score(len(incident_ids), scam_types)

        packages.append(
            {
                "fraud_ring_id": f"RING-{ring_index:03d}",
                "ring_type": _ring_type(scam_types),
                "confidence_score": confidence,
                "core_members": core_members,
                "jurisdictions_affected": jurisdictions,
                "victim_regions": regions,
                "total_victims_reached": len(incident_ids),
                "total_amount_requested": total_demanded,
                "total_amount_requested_formatted": _format_inr(total_demanded),
                "total_amount_lost": total_lost,
                "total_amount_lost_formatted": _format_inr(total_lost),
                "operation_timeframe": {
                    "start": timestamps[0] if timestamps else None,
                    "end": timestamps[-1] if timestamps else None,
                },
                "mule_account_network": mule_account_network,
                "phone_call_network": phone_call_network,
                "incident_timeline": incident_timeline,
                "evidence_chain": evidence_chain,
            }
        )

    packages.sort(key=lambda p: p["total_victims_reached"], reverse=True)
    return packages
