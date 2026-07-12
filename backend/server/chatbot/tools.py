from typing import Literal

from langchain_core.tools import BaseTool, tool

from server.chatbot.link_safety import check_gsb, check_vt
from server.chatbot.retrieval import retrieve
from server.models.incident import Incident
from server.repositories.incident_repo import IncidentRepository

_REPORT_FIELDS = [
    "caller_number",
    "mule_account",
    "mule_upi",
    "victim_region",
    "scam_type",
]


@tool
async def check_link_safety(url: str) -> str:
    """Check whether a URL shared by the user is safe or malicious.
    Call this whenever the user pastes or mentions any link/URL.
    Returns a verdict (safe/unsafe), threat type if flagged, and VirusTotal stats."""
    try:
        gsb, vt = await check_gsb(url), await check_vt(url)
        overall_safe = gsb["safe"] and (vt["safe"] is not False)
        verdict = "SAFE" if overall_safe else "UNSAFE ⚠️"
        parts = [f"Link verdict: {verdict}", f"URL: {url}"]
        if not gsb["safe"] and gsb.get("threat"):
            parts.append(f"Google Safe Browsing: flagged as {gsb['threat'].replace('_', ' ').lower()}")
        else:
            parts.append("Google Safe Browsing: clean")
        if vt.get("note") == "queued":
            parts.append("VirusTotal: URL submitted for scanning (check back later)")
        else:
            mal, sus = vt.get("malicious", 0), vt.get("suspicious", 0)
            parts.append(f"VirusTotal: {mal} malicious, {sus} suspicious detections")
        return "\n".join(parts)
    except Exception as e:
        return f"Could not check link: {e}"


@tool
def search_fraud_knowledge(query: str) -> str:
    """Look up fraud-advisory guidance relevant to the user's situation: scam
    patterns, red flags, what to do, and how/where to report. Call this before
    giving safety advice so the reply is grounded in real guidance, not guessed."""
    hits = retrieve(query)
    return "\n\n".join(hits) if hits else "(no relevant guidance found)"


def build_chat_tools(
    incidents: IncidentRepository, *, session_id: str, user_id: str | None
) -> list[BaseTool]:
    @tool
    async def save_incident(
        scam_type: Literal[
            "digital_arrest",
            "courier_parcel",
            "kyc",
            "upi",
            "job",
            "investment",
            "lottery",
            "other",
        ]
        | None = None,
        caller_number: str | None = None,
        mule_account: str | None = None,
        mule_upi: str | None = None,
        victim_region: str | None = None,
        claimed_authority: str | None = None,
        amount_demanded: float | None = None,
        amount_lost: float | None = None,
        payment_method: str | None = None,
        remote_app_requested: str | None = None,
    ) -> str:
        """Record scam details the user has given. Call this as soon as the user
        reveals any field, and again as more details come out. Pass only fields
        actually stated; leave the rest null. Never put the same value in two of
        caller_number / mule_account / mule_upi.

        - caller_number: phone number the scammer called from
        - mule_account: bank account the user was told to pay (the number, or the bank name if that's all)
        - mule_upi: UPI handle the user was told to pay
        - victim_region: the user's city / area
        - claimed_authority: who the caller claimed to be (CBI, bank, police, courier...)
        - amount_demanded / amount_lost: rupee amounts
        - payment_method, remote_app_requested: e.g. UPI / "AnyDesk"
        """
        incident = await incidents.get(session_id) or Incident(
            session_id=session_id, user_id=user_id
        )
        incident.merge_extracted(
            {
                "scam_type": scam_type,
                "caller_number": caller_number,
                "mule_account": mule_account,
                "mule_upi": mule_upi,
                "victim_region": victim_region,
                "claimed_authority": claimed_authority,
                "amount_demanded": amount_demanded,
                "amount_lost": amount_lost,
                "payment_method": payment_method,
                "remote_app_requested": remote_app_requested,
            }
        )
        await incidents.upsert(incident)
        missing = [f for f in _REPORT_FIELDS if getattr(incident, f) is None]
        return f"saved; still missing: {', '.join(missing) or 'nothing key'}"

    @tool
    async def update_incident(
        scam_type: Literal[
            "digital_arrest",
            "courier_parcel",
            "kyc",
            "upi",
            "job",
            "investment",
            "lottery",
            "other",
        ]
        | None = None,
        caller_number: str | None = None,
        mule_account: str | None = None,
        mule_upi: str | None = None,
        victim_region: str | None = None,
        claimed_authority: str | None = None,
        amount_demanded: float | None = None,
        amount_lost: float | None = None,
        payment_method: str | None = None,
        remote_app_requested: str | None = None,
    ) -> str:
        """Correct a detail already recorded, when the user explicitly changes
        it ("the account was actually X, not Y"). Use ONLY for such corrections,
        not for adding new details — use save_incident for new details. Pass
        only the field(s) being corrected."""
        incident = await incidents.get(session_id)
        if incident is None:
            return "nothing recorded yet; use save_incident"
        incident.overwrite(
            {
                "scam_type": scam_type,
                "caller_number": caller_number,
                "mule_account": mule_account,
                "mule_upi": mule_upi,
                "victim_region": victim_region,
                "claimed_authority": claimed_authority,
                "amount_demanded": amount_demanded,
                "amount_lost": amount_lost,
                "payment_method": payment_method,
                "remote_app_requested": remote_app_requested,
            }
        )
        await incidents.upsert(incident)
        return "updated"

    @tool
    async def lookup_fraud_network(value: str) -> str:
        """Check whether a phone number, bank account, or UPI id has shown up in
        OTHER reported scams. Call this when the user names a specific number /
        account / UPI, so you can warn them if it's already known. Returns how
        many prior reports mention it and what it's linked to."""
        info = await incidents.lookup_entity(value, exclude_session=session_id)
        if info["report_count"] == 0:
            return f"{value}: not seen in any other report yet."
        return (
            f"{value}: appears in {info['report_count']} other report(s); "
            f"seen as {info['seen_as']}; scam types {info['scam_types']}; "
            f"linked to {info['linked_entities']}"
        )

    return [
        check_link_safety,
        search_fraud_knowledge,
        save_incident,
        update_incident,
        lookup_fraud_network,
    ]
