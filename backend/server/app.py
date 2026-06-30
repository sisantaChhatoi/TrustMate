from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.repositories.chat_repo import ChatRepository
from server.repositories.incident_repo import IncidentRepository
from server.repositories.user_repo import UserRepository
from server.routers import auth, chatbot, intelligence, test
from shared.db import get_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = get_database()
    await UserRepository(db).ensure_indexes()
    await ChatRepository(db).ensure_indexes()
    await IncidentRepository(db).ensure_indexes()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ScamCall API", lifespan=lifespan)
    app.include_router(auth.router)
    app.include_router(chatbot.router)
    app.include_router(intelligence.router)
    app.include_router(test.router)
    return app


app = create_app()
