"""Standalone link-safety helpers — no FastAPI deps, safe to import from tools."""

import base64

import httpx

from shared.config import settings

_GSB_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
_VT_URL = "https://www.virustotal.com/api/v3/urls"


async def check_gsb(url: str) -> dict:
    body = {
        "client": {"clientId": "digital-arrest-shield", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            _GSB_URL, params={"key": settings.google_safe_browsing_key}, json=body
        )
        r.raise_for_status()
        matches = r.json().get("matches", [])
        if matches:
            return {"safe": False, "threat": matches[0].get("threatType", "UNKNOWN")}
        return {"safe": True, "threat": None}


async def check_vt(url: str) -> dict:
    url_id = base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()
    headers = {"x-apikey": settings.virustotal_key}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{_VT_URL}/{url_id}", headers=headers)
        if r.status_code == 404:
            submit = await client.post(_VT_URL, headers=headers, data={"url": url})
            submit.raise_for_status()
            return {"safe": None, "malicious": 0, "suspicious": 0, "note": "queued"}
        r.raise_for_status()
        stats = r.json()["data"]["attributes"]["last_analysis_stats"]
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        return {
            "safe": malicious == 0 and suspicious == 0,
            "malicious": malicious,
            "suspicious": suspicious,
            "note": None,
        }
