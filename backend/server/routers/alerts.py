from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from server.deps import get_db, get_notification_service
from server.repositories.user_repo import UserRepository
from server.services.notification_service import NotificationService, PushError
from shared.config import settings

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertPayload(BaseModel):
    user_id: str
    scam: bool
    confidence: float
    reason: str
    red_flags: list[str]
    caller: str | None = None


@router.post("", status_code=202)
async def receive_alert(
    payload: AlertPayload,
    x_internal_key: str = Header(...),
    db=Depends(get_db),
    svc: NotificationService = Depends(get_notification_service),
) -> dict:
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=403, detail="forbidden")

    user = await UserRepository(db).get_by_id(payload.user_id)
    if not user or not user.push_token:
        return {"status": "no_token"}

    try:
        await svc.send_push(
            user.push_token,
            title="⚠️ Scam detected on your call",
            body=payload.reason,
            data={
                "type": "scam_alert",
                "confidence": payload.confidence,
                "reason": payload.reason,
                "red_flags": payload.red_flags,
                "caller": payload.caller,
            },
        )
    except PushError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"status": "sent"}
