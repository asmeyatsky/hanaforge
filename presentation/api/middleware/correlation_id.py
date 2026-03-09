"""Correlation ID middleware — propagates a unique request identifier.

Extracts ``X-Request-ID`` from the incoming request headers or generates a
new UUID-4.  The value is stored in a :mod:`contextvars` ``ContextVar`` so
that loggers and error handlers can include it automatically.  The same
value is returned to the caller via the ``X-Request-ID`` response header.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from infrastructure.logging.structured_logger import correlation_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Inject a correlation ID into every request/response cycle."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Prefer client-supplied ID; fall back to a fresh UUID.
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Store in contextvars for logging / error handlers.
        token = correlation_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            correlation_id_ctx.reset(token)
