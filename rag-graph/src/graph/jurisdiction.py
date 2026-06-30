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
    # NCRB's 34-city baseline (fetch_ncrb_data.py) -- added for jurisdiction
    # lookups on that dataset, not just chat-collected victim_region.
    "agra": "Uttar Pradesh",
    "amritsar": "Punjab",
    "asansol": "West Bengal",
    "aurangabad": "Maharashtra",
    "chandigarh city": "Chandigarh",
    "dhanbad": "Jharkhand",
    "durg-bhilainagar": "Chhattisgarh",
    "faridabad": "Haryana",
    "gwalior": "Madhya Pradesh",
    "jabalpur": "Madhya Pradesh",
    "jamshedpur": "Jharkhand",
    "jodhpur": "Rajasthan",
    "kannur": "Kerala",
    "kollam": "Kerala",
    "kota": "Rajasthan",
    "ludhiana": "Punjab",
    "madurai": "Tamil Nadu",
    "malappuram": "Kerala",
    "meerut": "Uttar Pradesh",
    "nasik": "Maharashtra",
    "prayagraj": "Uttar Pradesh",
    "raipur": "Chhattisgarh",
    "rajkot": "Gujarat",
    "ranchi": "Jharkhand",
    "srinagar": "Jammu and Kashmir",
    "thiruvananthapuram": "Kerala",
    "thrissur": "Kerala",
    "tiruchirapalli": "Tamil Nadu",
    "vadodara": "Gujarat",
    "varanasi": "Uttar Pradesh",
    "vasai virar": "Maharashtra",
    "vijayawada": "Andhra Pradesh",
    "vishakhapatnam": "Andhra Pradesh",
    "muzaffarpur": "Bihar",
    "gaya": "Bihar",
    "bhagalpur": "Bihar",
    "darbhanga": "Bihar",
    "gorakhpur": "Uttar Pradesh",
    "allahabad": "Uttar Pradesh",
    "moradabad": "Uttar Pradesh",
    "aligarh": "Uttar Pradesh",
    "bareilly": "Uttar Pradesh",
    "saharanpur": "Uttar Pradesh",
}


def map_region_to_jurisdiction(region: str | None) -> str:
    if not region:
        return "Unknown"
    key = region.strip().lower()
    if key in CITY_TO_STATE:
        return CITY_TO_STATE[key]
    # User may have typed "Muzaffarpur, Bihar" — try just the part before the comma
    city_part = key.split(",")[0].strip()
    return CITY_TO_STATE.get(city_part, "Unknown")
