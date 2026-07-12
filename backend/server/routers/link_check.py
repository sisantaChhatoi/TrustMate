"""Link safety checker — Google Safe Browsing + VirusTotal."""

from fastapi import APIRouter, Depends

from server.chatbot.link_safety import check_gsb, check_vt
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

    gsb, vt = await check_gsb(url), await check_vt(url)

    overall_safe = gsb["safe"] and (vt["safe"] is not False)
    verdict = "safe" if overall_safe else "unsafe"

    return {
        "url": url,
        "verdict": verdict,
        "google_safe_browsing": gsb,
        "virustotal": vt,
    }
