"""Maps a free-text victim_region (a city name, as typed by the user during
the chat -- there's no administrative boundary data behind it) to an Indian
state, so multi-state ring activity can be flagged for the right
cyber-cell/agency. Best-effort, static lookup -- unrecognized cities map to
"Unknown", not a guess.
"""

from __future__ import annotations

CITY_TO_STATE = {
    "mumbai": "Maharashtra",
    "pune": "Maharashtra",
    "nagpur": "Maharashtra",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "bangalore": "Karnataka",
    "bengaluru": "Karnataka",
    "chennai": "Tamil Nadu",
    "kolkata": "West Bengal",
    "hyderabad": "Telangana",
    "jaipur": "Rajasthan",
    "patna": "Bihar",
    "indore": "Madhya Pradesh",
    "bhopal": "Madhya Pradesh",
    "surat": "Gujarat",
    "ahmedabad": "Gujarat",
    "kanpur": "Uttar Pradesh",
    "lucknow": "Uttar Pradesh",
    "chandigarh": "Chandigarh",
}


def map_region_to_jurisdiction(region: str | None) -> str:
    if not region:
        return "Unknown"
    return CITY_TO_STATE.get(region.strip().lower(), "Unknown")
