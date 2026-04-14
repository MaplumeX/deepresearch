from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.chat_manager import ChatConversationManager
from app.config import get_settings
from app.run_manager import ResearchRunManager
from app.run_store import ResearchRunStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    store = ResearchRunStore(settings.runs_db_path)
    run_manager = ResearchRunManager(settings, store=store)
    chat_manager = ChatConversationManager(settings, store=store)
    await run_manager.initialize()
    await chat_manager.initialize()
    app.state.conversation_store = store
    app.state.run_manager = run_manager
    app.state.chat_manager = chat_manager
    try:
        yield
    finally:
        await chat_manager.shutdown()
        await run_manager.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
