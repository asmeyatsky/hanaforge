"""HanaForge API — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """API root — service metadata."""
    return {
        "name": "HanaForge",
        "version": "1.0.0",
        "description": "AI-Native SAP S/4HANA Migration Platform",
    }
