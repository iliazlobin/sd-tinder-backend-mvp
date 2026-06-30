"""FastAPI application factory with lifespan and router mounting."""

from __future__ import annotations

import asyncio
import logging
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify DB connection with timeout. Shutdown: dispose engine."""
    engine = get_engine()
    logger.info("Lifespan startup: verifying database connectivity (timeout 10s) ...")
    try:
        async with asyncio.timeout(10):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        logger.info("Lifespan startup: database connectivity OK")
    except asyncio.TimeoutError:
        logger.error("Lifespan startup: database connection timed out after 10s")
        raise
    except Exception:
        logger.exception("Lifespan startup: database connection failed")
        raise
    yield
    logger.info("Lifespan shutdown: disposing engine")
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
