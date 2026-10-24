"""App factory: settings, database, middleware, routers under /api/v1."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from salary_api import __version__
from salary_api.core.config import Settings
from salary_api.core.db import create_db_engine, create_session_factory
from salary_api.core.logging import configure_logging
from salary_api.core.request_id import RequestIdMiddleware
from salary_api.modules.health.router import router as health_router

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        yield
        engine.dispose()

    app = FastAPI(
        title="ACME Salary Management API",
        version=__version__,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = create_session_factory(engine)

    app.add_middleware(RequestIdMiddleware)
    app.include_router(health_router, prefix=API_PREFIX)
    return app


app = create_app()
