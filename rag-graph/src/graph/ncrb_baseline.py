"""Loads the static NCRB city-wise cyber crime baseline (produced by
fetch_ncrb_data.py) and geocodes it, for use as the baseline density layer
under your own chat-collected fraud incidents -- see heatmap.py."""

from __future__ import annotations

import json
from pathlib import Path

from src.graph.geospatial import geocode_region
from src.graph.jurisdiction import map_region_to_jurisdiction

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "external" / "ncrb_cybercrime_city.json"


def load_ncrb_baseline() -> list[dict]:
    """Returns one entry per NCRB city with lat/lon attached. A city with
    no match in geospatial.CITY_TO_LATLONG is skipped (not silently
    dropped from the source data -- see fetch_ncrb_data.py's output for the
    raw, ungeocoded numbers)."""
    if not DATA_PATH.exists():
        raise RuntimeError(f"{DATA_PATH} not found -- run `python -m src.graph.fetch_ncrb_data` first.")

    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    geocoded = []
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
