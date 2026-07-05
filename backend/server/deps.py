from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.asynchronous.database import AsyncDatabase

from server.chatbot.engine import ChatbotEngine
from server.core.security import decode_access_token
from server.models.user import UserInDB
from server.repositories.chat_repo import ChatRepository
from server.repositories.incident_repo import IncidentRepository
from server.repositories.notification_repo import NotificationRepository
from server.repositories.user_repo import UserRepository
from server.services.auth_service import AuthService
from server.services.chatbot_service import ChatbotService
from server.services.notification_service import NotificationService
from shared.config import settings
from shared.db import get_database

_bearer = HTTPBearer(auto_error=False)


def get_db() -> AsyncDatabase:
    return get_database()


def get_user_repository(
    db: Annotated[AsyncDatabase, Depends(get_db)],
) -> UserRepository:
    return UserRepository(db)


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(users)


def get_chat_repository(
    db: Annotated[AsyncDatabase, Depends(get_db)],
) -> ChatRepository:
    return ChatRepository(db)


def get_incident_repository(
    db: Annotated[AsyncDatabase, Depends(get_db)],
) -> IncidentRepository:
    return IncidentRepository(db)


def get_notification_repository(
    db: Annotated[AsyncDatabase, Depends(get_db)],
) -> NotificationRepository:
    return NotificationRepository(db)


@lru_cache
def get_chatbot_engine() -> ChatbotEngine:
    return ChatbotEngine()


def get_chatbot_service(
    chats: Annotated[ChatRepository, Depends(get_chat_repository)],
    incidents: Annotated[IncidentRepository, Depends(get_incident_repository)],
    engine: Annotated[ChatbotEngine, Depends(get_chatbot_engine)],
) -> ChatbotService:
    return ChatbotService(chats, incidents, engine, settings.chat_history_limit)


def get_notification_service() -> NotificationService:
    return NotificationService()


async def get_current_user(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserInDB:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token: str = creds.credentials
    try:
        user_id = decode_access_token(token)
    except (jwt.InvalidTokenError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc
    user = await users.get_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user no longer exists")
    return user
