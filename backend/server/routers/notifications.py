from typing import Annotated

from fastapi import APIRouter, Depends

from server.deps import get_current_user, get_notification_repository
from server.models.notification import Notification
from server.models.user import UserInDB
from server.repositories.notification_repo import NotificationRepository

router = APIRouter(prefix="/notifications", tags=["notifications"])

_UserDep = Annotated[UserInDB, Depends(get_current_user)]
_RepoDep = Annotated[NotificationRepository, Depends(get_notification_repository)]


@router.get("", response_model=list[Notification])
async def list_notifications(user: _UserDep, repo: _RepoDep) -> list[Notification]:
    return await repo.list_for_user(user.user_id)
