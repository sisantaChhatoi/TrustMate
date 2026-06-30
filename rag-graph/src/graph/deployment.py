"""Ranks cities for patrol/resource deployment priority by combining the
NCRB national baseline with our own incident overlay -- a city that's high
on both is a stronger signal than either alone.

The combined score is a transparent, documented heuristic (same philosophy
as ring_intelligence.py's confidence score): it travels with the number,
it is not asserted as a verified risk determination.
"""

from __future__ import annotations

# Weights: NCRB's crime_rate_2023 (per-lakh-population, so already
# normalized for city size) carries more weight than our own incident_count
# (a handful of self-reported chat incidents, not a per-capita rate) --
# the NCRB figure is the more statistically grounded of the two right now.
_NCRB_WEIGHT = 0.7
_OUR_INCIDENTS_WEIGHT = 0.3

TOP_N_DEPLOYMENT_ZONES = 10


def _normalize(values: list[float]) -> dict[int, float]:
    """Min-max normalizes a list of values to 0..1 by index, so two
    differently-scaled signals (a per-lakh rate vs a raw incident count)
    can be combined without one dominating purely due to units."""
    if not values:
        return {}
    lo, hi = min(values), max(values)
    if hi == lo:
        return {i: 0.0 for i in range(len(values))}
    return {i: (v - lo) / (hi - lo) for i, v in enumerate(values)}


def build_deployment_strategy(ncrb_baseline: list[dict], hotspots: list[dict]) -> dict:
    hotspot_by_region = {h["region"].strip().lower(): h for h in hotspots}

    ncrb_rates = [c["crime_rate_2023"] for c in ncrb_baseline]
    ncrb_norm = _normalize(ncrb_rates)

    zones = []
    for i, city in enumerate(ncrb_baseline):
        region_key = city["city"].strip().lower()
        matched_hotspot = hotspot_by_region.get(region_key)
        our_incident_count = matched_hotspot["incident_count"] if matched_hotspot else 0
        zones.append(
            {
                "city": city["city"],
                "state": city["state"],
                "lat": city["lat"],
                "lon": city["lon"],
                "ncrb_crime_rate_2023": city["crime_rate_2023"],
                "ncrb_cases_2023": city["cases_2023"],
                "our_incident_count": our_incident_count,
                "_ncrb_norm": ncrb_norm[i],
            }
        )

    our_counts = [z["our_incident_count"] for z in zones]
    our_norm = _normalize(our_counts)
    for i, zone in enumerate(zones):
        zone["combined_risk_score"] = round(
            _NCRB_WEIGHT * zone.pop("_ncrb_norm") + _OUR_INCIDENTS_WEIGHT * our_norm[i], 4
        )

    zones.sort(key=lambda z: z["combined_risk_score"], reverse=True)
    top_zones = zones[:TOP_N_DEPLOYMENT_ZONES]
    for rank, zone in enumerate(top_zones, start=1):
        zone["deployment_priority_rank"] = rank

    # Our own incidents in a region the NCRB baseline doesn't cover at all
    # (e.g. a city outside NCRB's 34-city list) are real signal that the
    # weighted ranking above can't see -- surfaced separately so they're
    # not silently lost.
    uncovered = [
        {"region": h["region"], "state": h["state"], "incident_count": h["incident_count"]}
        for h in hotspots
        if h["region"].strip().lower() not in {c["city"].strip().lower() for c in ncrb_baseline}
    ]

    return {
        "methodology": (
            f"combined_risk_score = {_NCRB_WEIGHT} * normalized(NCRB crime_rate_2023) "
            f"+ {_OUR_INCIDENTS_WEIGHT} * normalized(our incident_count). "
            "A documented heuristic for prioritization, not a verified risk determination."
        ),
        "top_deployment_zones": top_zones,
        "our_incidents_outside_ncrb_coverage": uncovered,
    }
