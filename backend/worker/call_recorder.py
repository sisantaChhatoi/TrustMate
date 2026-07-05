import logging
from datetime import UTC, datetime

import httpx
from livekit import rtc
from livekit.agents import JobContext

from shared.config import settings
from shared.detector import Detection
from shared.repositories.call_repo import CallRepository
from shared.repositories.user_directory import UserDirectory

logger = logging.getLogger("scamcall.recorder")

# inbound-SIP caller number lands in one of these; identity is the fallback
_SIP_PHONE_KEYS = ("sip.phoneNumber", "sip.from", "sip.fromNumber")


def _participant_phone(p: rtc.Participant) -> str | None:
    attrs = p.attributes or {}
    for key in _SIP_PHONE_KEYS:
        if attrs.get(key):
            return attrs[key]
    return p.identity or None


class CallRecorder:
    def __init__(
        self, ctx: JobContext, calls: CallRepository, users: UserDirectory
    ) -> None:
        self._ctx = ctx
        self._calls = calls
        self._users = users
        self._room = ctx.room.name
        self._user_id: str | None = None

    async def sync(self) -> None:
        remotes = list(self._ctx.room.remote_participants.values())
        for p in remotes:
            logger.info(
                "participant identity=%r attributes=%r",
                p.identity,
                dict(p.attributes or {}),
            )

        user_phone: str | None = None
        user_id: str | None = None
        for p in remotes:
            phone = _participant_phone(p)
            resolved = await self._users.user_id_for_phone(phone)
            if resolved:
                user_phone, user_id = phone, resolved
                break

        self._user_id = user_id
        await self._calls.start(
            self._room,
            user_phone=user_phone,
            user_id=user_id,
            started_at=datetime.now(UTC),
        )
        if user_id is None:
            logger.warning(
                "no registered user matched a caller in room %r; alerts will be skipped",
                self._room,
            )

    async def on_alert(
        self, participant: rtc.RemoteParticipant, detection: Detection, window: str
    ) -> None:
        logger.warning(
            "SCAM caller=%s confidence=%.2f reason=%s red_flags=%s",
            participant.identity,
            detection.confidence,
            detection.reason,
            detection.red_flags,
        )
        try:
            if self._user_id is None:
                logger.warning(
                    "scam in room %r but no user_id; not notifying", self._room
                )
                return
            claimed = await self._calls.claim_notification(
                self._room, datetime.now(UTC), settings.alert_throttle_seconds
            )
            if not claimed:
                logger.info(
                    "alert throttled for room %r (within %.0fs)",
                    self._room,
                    settings.alert_throttle_seconds,
                )
                return
            await self._post_alert(detection)
        except Exception:
            logger.exception("alert handling failed for room %r", self._room)

    async def _post_alert(self, detection: Detection) -> None:
        payload = {
            "user_id": self._user_id,
            "confidence": detection.confidence,
            "reason": detection.reason,
            "red_flags": detection.red_flags,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                settings.alert_intake_url,
                json=payload,
                headers={"X-Internal-Key": settings.internal_api_key},
            )
        if res.status_code >= httpx.codes.BAD_REQUEST:
            logger.error("alert intake failed (%s): %s", res.status_code, res.text)

    async def finish(self) -> None:
        try:
            await self._calls.end(self._room, datetime.now(UTC))
        except Exception:
            logger.exception("failed to close call record for room %r", self._room)
