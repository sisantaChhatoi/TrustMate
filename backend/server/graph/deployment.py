"""Patrol-deployment ranking: NCRB baseline weighted with our incident
overlay."""

# NCRB rate is per-lakh (size-normalized), so it outweighs our raw counts.
_NCRB_WEIGHT = 0.7
_OUR_INCIDENTS_WEIGHT = 0.3

TOP_N_DEPLOYMENT_ZONES = 10


def _normalize(values: list[float]) -> dict[int, float]:
    """Min-max normalize to 0..1 by index, so two differently-scaled signals
    combine without one dominating purely on units."""
    if not values:
        return {}
    lo, hi = min(values), max(values)
    if hi == lo:
        return {i: 0.0 for i in range(len(values))}
    return {i: (v - lo) / (hi - lo) for i, v in enumerate(values)}


def build_deployment_strategy(ncrb_baseline: list[dict], hotspots: list[dict]) -> dict:
    hotspot_by_region = {h["region"].strip().lower(): h for h in hotspots}

    ncrb_norm = _normalize([c["crime_rate_2023"] for c in ncrb_baseline])

    zones: list[dict] = []
    for i, city in enumerate(ncrb_baseline):
        region_key = city["city"].strip().lower()
        matched = hotspot_by_region.get(region_key)
        zones.append(
            {
                "city": city["city"],
                "state": city["state"],
                "lat": city["lat"],
                "lon": city["lon"],
                "ncrb_crime_rate_2023": city["crime_rate_2023"],
                "ncrb_cases_2023": city["cases_2023"],
                "our_incident_count": matched["incident_count"] if matched else 0,
                "_ncrb_norm": ncrb_norm[i],
            }
        )

    our_norm = _normalize([z["our_incident_count"] for z in zones])
    for i, zone in enumerate(zones):
        zone["combined_risk_score"] = round(
            _NCRB_WEIGHT * zone.pop("_ncrb_norm") + _OUR_INCIDENTS_WEIGHT * our_norm[i],
            4,
        )

    zones.sort(key=lambda z: z["combined_risk_score"], reverse=True)
    top_zones = zones[:TOP_N_DEPLOYMENT_ZONES]
    for rank, zone in enumerate(top_zones, start=1):
        zone["deployment_priority_rank"] = rank

    # Our incidents in a region NCRB doesn't cover are real signal the
    # weighted ranking can't see -- surfaced separately so they aren't lost.
    ncrb_cities = {c["city"].strip().lower() for c in ncrb_baseline}
    uncovered = [
        {
            "region": h["region"],
            "state": h["state"],
            "incident_count": h["incident_count"],
        }
        for h in hotspots
        if h["region"].strip().lower() not in ncrb_cities
    ]

    return {
        "methodology": (
            f"combined_risk_score = {_NCRB_WEIGHT} * normalized(NCRB crime_rate_2023) "
            f"+ {_OUR_INCIDENTS_WEIGHT} * normalized(our incident_count). "
            "A documented heuristic for prioritization, not a verified determination."
        ),
        "top_deployment_zones": top_zones,
        "our_incidents_outside_ncrb_coverage": uncovered,
    }
