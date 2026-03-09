"""Structured JSON logging — production-ready logging with correlation ID support.

Uses Python's standard ``logging`` library with a custom JSON formatter.
In development mode (``HANAFORGE_LOG_FORMAT=text``), emits human-readable logs;
in production (``HANAFORGE_LOG_FORMAT=json``, the default), emits single-line JSON.

Correlation IDs are propagated via :mod:`contextvars` so that all log entries
within a single request share the same ``correlation_id``.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Correlation ID context variable — set by the correlation-ID middleware
# ---------------------------------------------------------------------------
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------
class _JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "logger": record.name,
            "correlation_id": correlation_id_ctx.get(""),
        }
        # Merge any extra fields attached by the caller.
        if hasattr(record, "extra_fields"):
            payload.update(record.extra_fields)  # type: ignore[arg-type]
        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _TextFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        cid = correlation_id_ctx.get("")
        cid_part = f" [{cid[:8]}]" if cid else ""
        base = f"{ts} {record.levelname:<8}{cid_part} {record.name}: {record.getMessage()}"
        if record.exc_info and record.exc_info[1] is not None:
            base += "\n" + self.formatException(record.exc_info)
        return base


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------
_configured = False


def _configure_root() -> None:
    """One-time configuration of the root ``hanaforge`` logger."""
    global _configured  # noqa: PLW0603
    if _configured:
        return
    _configured = True

    log_format = os.getenv("HANAFORGE_LOG_FORMAT", "json").lower()
    log_level = os.getenv("HANAFORGE_LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter() if log_format == "json" else _TextFormatter())

    root_logger = logging.getLogger("hanaforge")
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.addHandler(handler)
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``hanaforge`` namespace.

    Usage::

        from infrastructure.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Something happened", extra={"extra_fields": {"key": "value"}})
    """
    _configure_root()
    return logging.getLogger(f"hanaforge.{name}")
