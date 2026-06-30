"""Aggregates incidents into geocoded hotspots for the command-centre map
view: fraud-complaint density per region, for patrol prioritisation.

Geocoding uses Nominatim (OpenStreetMap) with a local JSON cache so any
Indian city/town that a victim types works automatically -- no hand-coded
list. Results are cached permanently in data/external/geocode_cache.json so
the API is only hit once per unique city name ever.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from src.graph.jurisdiction import map_region_to_jurisdiction

_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "external" / "geocode_cache.json"

# A region with this many or more incidents is flagged for prioritised
# patrol attention.
HOTSPOT_HIGH_RISK_THRESHOLD = 5

_geocode_cache: dict[str, tuple[float, float] | None] | None = None


def _load_cache() -> dict[str, tuple[float, float] | None]:
    global _geocode_cache
    if _geocode_cache is not None:
        return _geocode_cache
    if _CACHE_PATH.exists():
        raw = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        _geocode_cache = {k: tuple(v) if v is not None else None for k, v in raw.items()}
    else:
        _geocode_cache = {}
    return _geocode_cache


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _nominatim_lookup(query: str) -> tuple[float, float] | None:
    """One Nominatim call, India-scoped. Returns (lat, lon) or None."""
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderServiceError

        geolocator = Nominatim(user_agent="digital-arrest-shield")
        location = geolocator.geocode(f"{query}, India", timeout=10)
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception:
        return None


def geocode_region(region: str | None) -> tuple[float, float] | None:
    """Returns (lat, lon) for a city/region string, or None if unresolvable.
    Checks cache first; on a miss calls Nominatim and caches the result
    (including None, so repeated misses don't hit the API again)."""
    if not region:
        return None
    key = region.strip().lower()
    cache = _load_cache()
    if key in cache:
        return cache[key]
    # Cache miss -- call Nominatim. Respect the 1-req/s usage policy.
    time.sleep(1)
    coords = _nominatim_lookup(key)
    cache[key] = coords
    _geocode_cache[key] = coords  # keep in-process cache in sync
    _save_cache(cache)
    return coords


def _safe_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_hotspots(incidents: list[dict]) -> tuple[list[dict], int]:
    """Returns (hotspots, ungeocoded_count). Each hotspot aggregates every
    incident whose victim_region resolves to a known city, sorted by
    incident_count descending."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    coords_map: dict[str, tuple[float, float]] = {}
    ungeocoded_count = 0

    for incident in incidents:
        region = incident.get("victim_region")
        coords = geocode_region(region)
        if coords is None:
            if region:
                ungeocoded_count += 1
            continue
        key = region.strip().lower()
        buckets[key].append(incident)
        coords_map[key] = coords

    hotspots = []
    for region_key, members in buckets.items():
        lat, lon = coords_map[region_key]
        scam_types = sorted({m["scam_type"] for m in members if m.get("scam_type")})
        incident_count = len(members)
        hotspots.append(
            {
                "region": region_key.title(),
                "state": map_region_to_jurisdiction(region_key),
                "lat": lat,
                "lon": lon,
                "incident_count": incident_count,
                "total_amount_demanded": sum(_safe_float(m.get("amount_demanded")) for m in members),
                "total_amount_lost": sum(_safe_float(m.get("amount_lost")) for m in members),
                "scam_types": scam_types,
                "risk_level": "high" if incident_count >= HOTSPOT_HIGH_RISK_THRESHOLD else "normal",
            }
        )

    hotspots.sort(key=lambda h: h["incident_count"], reverse=True)
    return hotspots, ungeocoded_count


def build_geojson(hotspots: list[dict]) -> dict:
    """GeoJSON FeatureCollection -- coordinates are [lon, lat] per the
    GeoJSON spec (the reverse of how lat/lon are usually written)."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [h["lon"], h["lat"]]},
                "properties": {k: v for k, v in h.items() if k not in ("lat", "lon")},
            }
            for h in hotspots
        ],
    }
