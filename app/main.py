from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.run_manager import ResearchRunManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = ResearchRunManager(get_settings())
    await manager.initialize()
    app.state.run_manager = manager
    try:
        yield
    finally:
        await manager.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
