"""HanaForge API — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.config.dependency_injection import Container
from presentation.api.routes import abap_analysis, discovery, programmes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: initialise the DI container on startup."""
    app.state.container = Container()
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
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev-only: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(programmes.router, prefix="/api/v1/programmes")
app.include_router(discovery.router, prefix="/api/v1/discovery")
app.include_router(abap_analysis.router, prefix="/api/v1/abap-analysis")


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
