"""Request/response logging middleware — structured access logs.

Logs every inbound HTTP request with method, path, status code, and
wall-clock duration.  The ``/health`` endpoint is excluded to reduce noise
from orchestrator probes.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from infrastructure.logging import get_logger

logger = get_logger("middleware.request")

# Paths to exclude from access logging (e.g. liveness probes).
_SKIP_PATHS: frozenset[str] = frozenset({"/health"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and duration for every HTTP request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "extra_fields": {
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code,
                    "duration_ms": duration_ms,
                },
            },
        )
        return response
