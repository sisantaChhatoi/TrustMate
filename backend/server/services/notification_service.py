import logging

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)


class PushError(Exception):
    pass


class NotificationService:
    async def send_push(
        self,
        push_token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        payload = {
            "to": push_token,
            "title": title,
            "body": body,
            "sound": "default",
            "channelId": "default",
            "priority": "high",
            "data": data or {},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(settings.expo_push_url, json=payload)
        if res.status_code != httpx.codes.OK:
            logger.error("expo push failed (%s): %s", res.status_code, res.text)
            raise PushError(f"expo push returned {res.status_code}")

        ticket = res.json().get("data", {})
        if ticket.get("status") == "error":
            logger.error("expo push ticket error: %s", ticket)
            raise PushError(ticket.get("message", "expo push ticket error"))
