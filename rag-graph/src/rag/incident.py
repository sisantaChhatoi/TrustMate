"""Pydantic schema for a scam incident collected through the RAG chat.

One Incident per chat session, filled in incrementally as the victim reveals
details during conversation. caller_number and mule_account are the
highest-priority fields — they're the entities the future graph module links
across incidents to find shared fraud infrastructure.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# A bare bank name ("SBI", "HDFC") has no long digit run -- a real account
# number does. Used to tell the two apart so we can probe once for the real
# number before falling back to accepting just the bank name.
_ACCOUNT_NUMBER_PATTERN = re.compile(r"\d{6,}")


class ScamType(str, Enum):
    DIGITAL_ARREST = "digital_arrest"
    COURIER_PARCEL = "courier_parcel"
    KYC = "kyc"
    UPI = "upi"
    JOB = "job"
    INVESTMENT = "investment"
    LOTTERY = "lottery"
    OTHER = "other"


class IncidentStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    REPORTED = "reported"
    COMPLETED = "completed"


# Order matters: chat.py walks this list to pick the next field to gently ask
# about, prioritizing the entities the graph module needs most. victim_region
# sits right after the three graph-critical fields (not last) so it reliably
# gets asked within the first few turns of any conversation, instead of
# requiring 6+ other fields to be resolved first before its turn ever comes.
EXTRACTABLE_FIELDS = [
    "caller_number",
    "mule_account",
    "mule_upi",
    "victim_region",
    "scam_type",
    "claimed_authority",
    "amount_demanded",
    "amount_lost",
    "payment_method",
    "remote_app_requested",
]


class Incident(BaseModel):
    incident_id: UUID = Field(default_factory=uuid4)
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    scam_type: ScamType | None = None
    claimed_authority: str | None = None
    caller_number: str | None = None
    mule_account: str | None = None
    mule_account_bank_name: str | None = None
    mule_account_followup_asked: bool = False
    mule_upi: str | None = None
    amount_demanded: float | None = None
    amount_lost: float | None = None
    victim_region: str | None = None
    payment_method: str | None = None
    remote_app_requested: str | None = None
    fields_asked: list[str] = Field(default_factory=list)
    status: IncidentStatus = IncidentStatus.IN_PROGRESS
    raw_conversation: str = ""

    def next_missing_field(self) -> str | None:
        """Each field is nudged AT MOST ONCE ever (tracked via fields_asked,
        set the moment a question is actually built into a reply -- see
        chat.py). If the user doesn't answer it that one time, we move on
        permanently rather than re-asking -- extraction still picks up a
        late answer from the transcript regardless, this only controls
        which question gets asked next.

        mule_account's bank-name-then-real-number followup is a deliberate,
        bounded exception: it's one extra try to finish the SAME question,
        not a new one, so it can fire even if "mule_account" is already in
        fields_asked -- but only once (see needs_account_number_followup)."""
        if self.needs_account_number_followup():
            return "mule_account"
        for field in EXTRACTABLE_FIELDS:
            if getattr(self, field) is None and field not in self.fields_asked:
                return field
        return None

    def needs_account_number_followup(self) -> bool:
        """True exactly once: when we have a bare bank name for mule_account
        but haven't yet gotten the actual account number, and haven't
        already used our one follow-up attempt."""
        return (
            self.mule_account is None
            and self.mule_account_bank_name is not None
            and not self.mule_account_followup_asked
        )

    def merge_extracted(self, updates: dict) -> None:
        """Updates fields from an extraction result. Fields are filled ONCE
        and then locked -- re-running extraction over a growing transcript
        can otherwise hallucinate a different (wrong) value for an
        already-answered field on a later turn, silently corrupting data
        that was already correct. scam_type is the deliberate exception: it
        genuinely can be misclassified early and clarified as the
        conversation reveals more, so it stays updatable."""
        for field in EXTRACTABLE_FIELDS:
            value = updates.get(field)
            if not _is_real_value(value):
                continue
            if field == "scam_type":
                try:
                    value = ScamType(value)
                except ValueError:
                    continue
                setattr(self, field, value)
            elif field == "mule_account":
                self._merge_mule_account(str(value))
            elif getattr(self, field) is None:
                setattr(self, field, value)

    def _merge_mule_account(self, value: str) -> None:
        if _ACCOUNT_NUMBER_PATTERN.search(value):
            # A real account number always wins outright, even over an
            # already-stored bank name.
            self.mule_account = value
            return
        if self.mule_account is not None:
            return  # already have a real number; a bank name can't downgrade it
        if self.mule_account_followup_asked:
            # The follow-up question ("what's the actual account number?")
            # has already been shown to the user at least once (tracked via
            # a flag set the moment the question is built, not by counting
            # extraction passes -- a single catch-up pass can process
            # several turns at once, so counting passes isn't reliable).
            # Still no qualifying number -- accept what we have rather than
            # asking forever.
            self.mule_account = self.mule_account_bank_name or value
        else:
            # First (or still unasked) sighting of just a bank name --
            # store/update it and keep mule_account null so the follow-up
            # gets asked once.
            self.mule_account_bank_name = value


_NULL_PLACEHOLDER_PHRASES = (
    "not explicitly stated",
    "not stated",
    "not mentioned",
    "not provided",
    "not specified",
    "unknown",
    "n/a",
    "none",
    "null",
)


def _is_real_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip().lower()
        return bool(stripped) and stripped not in _NULL_PLACEHOLDER_PHRASES
    return True
