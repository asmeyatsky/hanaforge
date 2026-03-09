"""Global exception handlers — map domain errors to structured HTTP responses.

Register these handlers on the FastAPI ``app`` instance during startup::

    from presentation.api.error_handlers import register_error_handlers
    register_error_handlers(app)

Every error response follows a consistent JSON envelope:

.. code-block:: json

    {
        "error": {
            "code": "ENTITY_NOT_FOUND",
            "message": "Programme 'abc' not found",
            "correlation_id": "d4e5f6...",
            "details": {}
        }
    }
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from domain.exceptions import (
    BusinessRuleViolationError,
    ConflictError,
    DomainError,
    EntityNotFoundError,
    ValidationError,
)
from infrastructure.logging import get_logger
from infrastructure.logging.structured_logger import correlation_id_ctx

logger = get_logger("error_handlers")

# ---------------------------------------------------------------------------
# HTTP status mapping
# ---------------------------------------------------------------------------
_STATUS_MAP: dict[type[DomainError], int] = {
    EntityNotFoundError: 404,
    ValidationError: 422,
    BusinessRuleViolationError: 400,
    ConflictError: 409,
}


def _build_error_response(code: str, message: str, details: dict, status_code: int) -> JSONResponse:
    """Build the canonical error JSON envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": correlation_id_ctx.get(""),
                "details": details,
            },
        },
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
async def _handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    """Handle any ``DomainError`` subclass with the appropriate HTTP status."""
    status_code = _STATUS_MAP.get(type(exc), 400)
    logger.warning(
        "Domain error [%s]: %s",
        exc.code,
        exc.message,
        extra={
            "extra_fields": {
                "error_code": exc.code,
                "error_details": exc.details,
                "http_status": status_code,
            },
        },
    )
    return _build_error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=status_code,
    )


async def _handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected errors — log the full traceback but return a
    sanitised 500 response so that internal details never leak to clients.
    """
    logger.error(
        "Unhandled exception: %s",
        str(exc),
        exc_info=True,
        extra={
            "extra_fields": {
                "error_type": type(exc).__name__,
                "http_path": request.url.path,
            },
        },
    )
    return _build_error_response(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        details={},
        status_code=500,
    )


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------
def register_error_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI application."""
    # Register the most specific subclasses first, then the base.
    for exc_cls in (
        EntityNotFoundError,
        ValidationError,
        BusinessRuleViolationError,
        ConflictError,
        DomainError,
    ):
        app.add_exception_handler(exc_cls, _handle_domain_error)  # type: ignore[arg-type]

    app.add_exception_handler(Exception, _handle_unhandled_exception)  # type: ignore[arg-type]
