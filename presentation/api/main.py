"""HanaForge API — FastAPI application entry point."""

from __future__ import annotations

import pathlib
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from infrastructure.config.dependency_injection import Container
from infrastructure.config.settings import get_settings
from presentation.api.error_handlers import register_error_handlers
from presentation.api.middleware.correlation_id import CorrelationIdMiddleware
from presentation.api.middleware.request_logging import RequestLoggingMiddleware
from presentation.api.routes import (
    abap_analysis,
    agents,
    auth,
    benchmarks,
    cutover,
    data_readiness,
    discovery,
    hana_bigquery,
    infrastructure,
    migration,
    programmes,
    rise,
    test_forge,
)

# Resolve the frontend build directory (exists after `npm run build` or in Docker).
_FRONTEND_DIST = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
_INDEX_HTML = _FRONTEND_DIST / "index.html"


class _SPAFallbackMiddleware(BaseHTTPMiddleware):
    """Intercept 404s for non-API GET requests and serve the SPA index.html.

    This runs as middleware (not a catch-all route) so it never shadows
    FastAPI's own route resolution, trailing-slash redirects, or error
    responses.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        if (
            response.status_code == 404
            and request.method == "GET"
            and not request.url.path.startswith("/api/")
            and _INDEX_HTML.is_file()
        ):
            last_segment = request.url.path.rsplit("/", 1)[-1]
            if "." in last_segment:
                # Static file request — serve from dist if it exists on disk
                candidate = _FRONTEND_DIST / request.url.path.lstrip("/")
                if candidate.is_file():
                    return FileResponse(candidate)
                return response
            return FileResponse(_INDEX_HTML)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: initialise the DI container on startup."""
    container = Container()
    app.state.container = container
    app.state.settings = container.settings
    yield


app = FastAPI(
    title="HanaForge API",
    version="1.0.0",
    description=(
        "AI-Native SAP S/4HANA Migration Platform. "
        "Provides intelligent discovery, ABAP code analysis, and guided remediation "
        "for large-scale SAP migrations on Google Cloud."
    ),
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
register_error_handlers(app)

# ---------------------------------------------------------------------------
# Middleware (order matters — outermost first)
# ---------------------------------------------------------------------------
if _FRONTEND_DIST.is_dir():
    app.add_middleware(_SPAFallbackMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)
_cors_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        _cors_settings.cors_allowed_origins.split(",") if _cors_settings.cors_allowed_origins != "*" else ["*"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(programmes.router, prefix="/api/v1/programmes")
app.include_router(hana_bigquery.router, prefix="/api/v1/programmes")
app.include_router(discovery.router, prefix="/api/v1/discovery")
app.include_router(abap_analysis.router, prefix="/api/v1/abap-analysis")
app.include_router(test_forge.router, prefix="/api/v1/test-forge")
app.include_router(data_readiness.router, prefix="/api/v1/data-readiness")
app.include_router(infrastructure.router, prefix="/api/v1/infrastructure")
app.include_router(migration.router, prefix="/api/v1/migration")
app.include_router(cutover.router, prefix="/api/v1/cutover")
app.include_router(agents.router, prefix="/api/v1/agents")
app.include_router(rise.router, prefix="/api/v1/rise")
app.include_router(benchmarks.router, prefix="/api/v1/benchmarks")


# ---------------------------------------------------------------------------
# Top-level endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Liveness / readiness probe."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/", tags=["Root"], response_model=None)
async def root() -> dict[str, str] | FileResponse:
    """Serve the SPA index.html when the frontend build exists, otherwise return API metadata."""
    index = _FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {
        "name": "HanaForge",
        "version": "1.0.0",
        "description": "AI-Native SAP S/4HANA Migration Platform",
    }


# ---------------------------------------------------------------------------
# SPA static assets (must come after API routes)
# ---------------------------------------------------------------------------
if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="static-assets")
    app.mount("/public", StaticFiles(directory=_FRONTEND_DIST), name="static-root")
