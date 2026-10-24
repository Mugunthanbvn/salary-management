"""App factory: settings, database, middleware, routers under /api/v1."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from salary_api import __version__
from salary_api.core.body_limit import BodySizeLimitMiddleware
from salary_api.core.config import Settings, load_settings
from salary_api.core.db import create_db_engine, create_session_factory
from salary_api.core.errors import (
    PROBLEM_RESPONSES,
    install_problem_handlers,
    use_problem_json_in_openapi,
)
from salary_api.core.logging import configure_logging
from salary_api.core.request_id import REQUEST_ID_HEADER, RequestIdMiddleware
from salary_api.modules.ask.router import router as ask_router
from salary_api.modules.auth.router import router as auth_router
from salary_api.modules.employees.router import router as employees_router
from salary_api.modules.exports.router import router as exports_router
from salary_api.modules.health.router import router as health_router
from salary_api.modules.imports.router import router as imports_router
from salary_api.modules.insights.router import router as insights_router
from salary_api.modules.reference.router import insights_router as bands_and_rates_router
from salary_api.modules.reference.router import router as reference_router
from salary_api.modules.salaries.router import router as salaries_router

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
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
        # No OAuth2 flow to redirect back to; FastAPI would serve it outside API_PREFIX.
        swagger_ui_oauth2_redirect_url=None,
        redoc_url=None,
        responses=PROBLEM_RESPONSES,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.session_factory = create_session_factory(engine)

    if settings.cors_origins:
        # Local development only: in production the browser calls the API through the
        # same-origin Next.js rewrite.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER],
        )
    app.add_middleware(BodySizeLimitMiddleware)  # inside RequestId: errors carry the id
    app.add_middleware(RequestIdMiddleware)  # added last, so it runs first
    install_problem_handlers(app)
    use_problem_json_in_openapi(app)
    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(reference_router, prefix=API_PREFIX)
    app.include_router(employees_router, prefix=API_PREFIX)
    app.include_router(exports_router, prefix=API_PREFIX)
    app.include_router(salaries_router, prefix=API_PREFIX)
    app.include_router(imports_router, prefix=API_PREFIX)
    app.include_router(insights_router, prefix=API_PREFIX)
    app.include_router(bands_and_rates_router, prefix=API_PREFIX)
    app.include_router(ask_router, prefix=API_PREFIX)
    return app


app = create_app()
