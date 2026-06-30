"""Static NCRB city-wise cybercrime baseline, geocoded."""

import json
from pathlib import Path

from server.graph.geospatial import geocode_region
from server.graph.jurisdiction import map_region_to_jurisdiction

DATA_PATH = Path(__file__).resolve().parent / "data" / "ncrb_cybercrime_city.json"


def load_ncrb_baseline() -> list[dict]:
    """One entry per NCRB city with lat/lon attached. A city that fails to
    geocode is skipped."""
    if not DATA_PATH.exists():
        return []

    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    geocoded: list[dict] = []
    for record in records:
        coords = geocode_region(record["city"])
        if coords is None:
            continue
        lat, lon = coords
        geocoded.append(
            {
                **record,
                "state": map_region_to_jurisdiction(record["city"]),
                "lat": lat,
                "lon": lon,
            }
        )
    return geocoded
