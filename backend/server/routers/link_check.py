"""Link safety checker — GSB + VirusTotal + Tier-1 heuristics + Tier-2 domain age + urlscan."""

import asyncio

from fastapi import APIRouter, Depends

from server.chatbot.link_safety import (
    analyze_url,
    check_domain_age,
    check_gsb,
    check_urlscan,
    check_vt,
    unshorten,
)
from server.deps import get_current_user

router = APIRouter(prefix="/link-check", tags=["link-check"])


@router.post("")
async def check_link(
    payload: dict,
    _: str = Depends(get_current_user),
) -> dict:
    url: str = payload.get("url", "").strip()
    if not url:
        return {"error": "url is required"}

    resolved = await unshorten(url)
    heuristics = analyze_url(resolved)

    gsb, vt, domain_age, urlscan = await asyncio.gather(
        check_gsb(resolved),
        check_vt(resolved),
        check_domain_age(resolved),
        check_urlscan(resolved),
        return_exceptions=True,
    )
    if isinstance(gsb, Exception):
        gsb = {"safe": True, "threat": None}
    if isinstance(vt, Exception):
        vt = {"safe": None, "malicious": 0, "suspicious": 0, "note": "unavailable"}
    if isinstance(domain_age, Exception):
        domain_age = {"age_days": None, "created": None, "domain": ""}
    if isinstance(urlscan, Exception):
        urlscan = {"scanned": False, "malicious": None, "score": None, "brands": [], "note": "error"}

    # Build combined score
    score = heuristics["score"]

    if not gsb["safe"]:
        score += 40
    if isinstance(vt.get("malicious"), int) and vt["malicious"] > 0:
        score += 40
    elif isinstance(vt.get("suspicious"), int) and vt["suspicious"] > 0:
        score += 20

    age_days = domain_age.get("age_days")
    if age_days is not None:
        if age_days < 30:
            score += 25
        elif age_days < 90:
            score += 10

    if urlscan.get("malicious"):
        score += 35
    elif isinstance(urlscan.get("score"), (int, float)) and urlscan["score"] > 50:
        score += 20

    combined_score = min(score, 100)
    risk_level = "high" if combined_score >= 60 else "suspicious" if combined_score >= 25 else "low"
    verdict = "unsafe" if risk_level == "high" else "suspicious" if risk_level == "suspicious" else "safe"

    return {
        "url": url,
        "resolved_url": resolved if resolved != url else None,
        "verdict": verdict,
        "risk_score": combined_score,
        "risk_level": risk_level,
        "flags": heuristics["flags"],
        "domain_age": domain_age,
        "urlscan": urlscan,
        "google_safe_browsing": gsb,
        "virustotal": vt,
    }
