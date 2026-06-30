"""FastAPI application factory with lifespan and router mounting."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from tinder.database import get_engine
from tinder.routers import (
    profile_router,
    feed_router,
    swipe_router,
    matches_router,
    messages_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify DB connection. Shutdown: dispose engine."""
    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tinder MVP",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        """Liveness probe — returns 200 unconditionally."""
        return JSONResponse(content={"status": "ok"})

    # Mount resource routers
    app.include_router(profile_router)
    app.include_router(feed_router)
    app.include_router(swipe_router)
    app.include_router(matches_router)
    app.include_router(messages_router)

    return app


app = create_app()
