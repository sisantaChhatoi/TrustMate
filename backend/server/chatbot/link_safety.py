"""Standalone link-safety helpers — no FastAPI deps, safe to import from tools."""

import asyncio
import base64
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from shared.config import settings

_GSB_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
_VT_URL = "https://www.virustotal.com/api/v3/urls"

_SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".tk", ".buzz", ".click", ".ml", ".ga", ".cf",
    ".gq", ".pw", ".icu", ".live", ".online", ".work", ".loan", ".win",
    ".bid", ".trade", ".racing", ".date", ".download", ".info",
}

_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "buff.ly",
    "tiny.cc", "is.gd", "rb.gy", "cutt.ly", "short.io", "clck.ru",
    "shorturl.at", "urlshrt.com", "tr.im",
}

_BRANDS = [
    "hdfc", "sbi", "icici", "axis", "kotak", "paytm", "phonepe",
    "gpay", "googlepay", "paypal", "amazon", "flipkart", "irctc",
    "uidai", "aadhar", "aadhaar", "epfo", "incometax", "nsdl",
    "facebook", "instagram", "whatsapp", "netflix", "apple",
]

_SCAM_KEYWORDS = {
    "login", "verify", "kyc", "otp", "refund", "prize", "reward",
    "secure", "update", "confirm", "account", "bank", "wallet",
    "winner", "claim", "gift", "lucky", "urgent", "alert", "suspend",
    "blocked", "freeze", "recover", "redeem",
}

_STANDARD_PORTS = {80, 443, 8080, 8443}


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


async def unshorten(url: str) -> str:
    """Follow redirects and return the final destination URL."""
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True, max_redirects=8) as client:
            r = await client.head(url)
            return str(r.url)
    except Exception:
        return url


def analyze_url(url: str) -> dict:
    """Return heuristic signals and a risk score (0–100) for a URL string."""
    flags: list[str] = []
    score = 0

    try:
        parsed = urlparse(url)
    except Exception:
        return {"flags": ["malformed URL"], "score": 40, "risk_level": "suspicious"}

    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    port = parsed.port
    parts = host.split(".")

    # Punycode / homoglyph domains
    if any(p.startswith("xn--") for p in parts):
        flags.append("lookalike domain (punycode/homoglyph characters)")
        score += 15

    # Non-ASCII chars in domain (e.g. Cyrillic lookalikes)
    try:
        host.encode("ascii")
    except UnicodeEncodeError:
        if not any(p.startswith("xn--") for p in parts):
            flags.append("non-ASCII characters in domain (visual lookalike)")
            score += 15

    # Raw IP address as host
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        flags.append("raw IP address instead of domain name")
        score += 15

    # @ in URL — classic credential-injection obfuscation
    if "@" in url:
        flags.append("@ symbol in URL (obfuscation trick)")
        score += 15

    # Non-standard port
    if port is not None and port not in _STANDARD_PORTS:
        flags.append(f"unusual port: {port}")
        score += 10

    # High-abuse TLD
    tld = f".{parts[-1]}" if parts else ""
    if tld in _SUSPICIOUS_TLDS:
        flags.append(f"high-abuse TLD ({tld})")
        score += 10

    # URL shortener — real destination was hidden before we unshortened
    bare = host.removeprefix("www.")
    if bare in _SHORTENERS:
        flags.append("URL shortener (destination was hidden)")
        score += 5

    # Typosquatting — edit-distance ≤ 2 to a known brand
    domain_label = parts[0] if len(parts) == 1 else parts[-2] if len(parts) >= 2 else host
    domain_label = domain_label.removeprefix("www")
    for brand in _BRANDS:
        if domain_label != brand and len(domain_label) >= 4 and _levenshtein(domain_label, brand) <= 2:
            flags.append(f"domain resembles '{brand}' (possible typosquat)")
            score += 20
            break

    # Scam keywords in domain + path
    combined = host + path
    hit = [kw for kw in _SCAM_KEYWORDS if kw in combined]
    if hit:
        flags.append(f"scam keywords in URL: {', '.join(hit[:4])}")
        score += min(10, len(hit) * 3)

    # Excessive subdomains (more than 3 labels → likely obfuscation)
    if len(parts) > 3:
        flags.append("many subdomains (e.g. legit-bank.scam.xyz.com)")
        score += 5

    # Excessive hyphens in the main domain label
    if domain_label.count("-") >= 2:
        flags.append("many hyphens in domain name")
        score += 5

    score = min(score, 100)
    risk_level = "high" if score >= 60 else "suspicious" if score >= 25 else "low"
    return {"flags": flags, "score": score, "risk_level": risk_level}


_TWO_LEVEL_TLDS = {
    "co.uk", "co.in", "co.jp", "co.nz", "co.za", "co.id",
    "com.au", "com.br", "net.in", "org.in",
}


def _registrable_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in _TWO_LEVEL_TLDS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


async def check_domain_age(url: str) -> dict:
    """Look up domain registration date via RDAP. Free, no API key needed."""
    try:
        host = (urlparse(url).hostname or "").lower()
        domain = _registrable_domain(host)
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            r = await client.get(f"https://rdap.org/domain/{domain}")
            if r.status_code != 200:
                return {"age_days": None, "created": None, "domain": domain}
            events = r.json().get("events", [])
            created_str = next(
                (e["eventDate"] for e in events if e.get("eventAction") == "registration"),
                None,
            )
            if not created_str:
                return {"age_days": None, "created": None, "domain": domain}
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created_dt).days
            return {
                "age_days": age_days,
                "created": created_dt.strftime("%Y-%m-%d"),
                "domain": domain,
            }
    except Exception:
        return {"age_days": None, "created": None, "domain": ""}


async def check_urlscan(url: str) -> dict:
    """Submit URL to urlscan.io and poll for verdict. Requires URLSCAN_API_KEY."""
    if not settings.urlscan_api_key:
        return {"scanned": False, "malicious": None, "score": None, "brands": [], "note": "no key"}
    headers = {"API-Key": settings.urlscan_api_key, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.post(
                "https://urlscan.io/api/v1/scan/",
                headers=headers,
                json={"url": url, "visibility": "unlisted"},
            )
            if r.status_code not in (200, 201):
                return {"scanned": False, "malicious": None, "score": None, "brands": [], "note": "submit failed"}
            uuid = r.json().get("uuid")
            if not uuid:
                return {"scanned": False, "malicious": None, "score": None, "brands": [], "note": "no uuid"}

            result_url = f"https://urlscan.io/api/v1/result/{uuid}/"
            for _ in range(5):
                await asyncio.sleep(3)
                res = await client.get(result_url)
                if res.status_code == 200:
                    v = res.json().get("verdicts", {}).get("overall", {})
                    return {
                        "scanned": True,
                        "malicious": v.get("malicious", False),
                        "score": v.get("score", 0),
                        "brands": v.get("brands", []),
                        "note": None,
                    }
            return {"scanned": True, "malicious": None, "score": None, "brands": [], "note": "timeout"}
    except Exception:
        return {"scanned": False, "malicious": None, "score": None, "brands": [], "note": "error"}


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
