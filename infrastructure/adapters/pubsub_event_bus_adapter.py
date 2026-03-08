"""InMemoryEventBusAdapter — dev-mode in-memory implementation of EventBusPort.

A Google Cloud Pub/Sub-backed adapter will replace this for production.  The
in-memory variant is useful for testing and local development where event
handlers run in the same process.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Callable

from domain.events.event_base import DomainEvent

logger = logging.getLogger(__name__)


class InMemoryEventBusAdapter:
    """Implements EventBusPort using an in-memory dict of handlers."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    async def publish(self, events: list[DomainEvent] | DomainEvent) -> None:
        """Publish one or more domain events to all registered handlers.

        Accepts either a single DomainEvent or a list for convenience,
        matching the port signature (list[DomainEvent]) while also handling
        the case where a use case passes a single event.
        """
        if isinstance(events, DomainEvent):
            events = [events]

        for event in events:
            event_type = type(event)
            handlers = self._handlers.get(event_type, [])

            for handler in handlers:
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception(
                        "Error in event handler %s for event %s",
                        handler.__name__,
                        event_type.__name__,
                    )

            # Also dispatch to handlers registered for the base DomainEvent type
            if event_type is not DomainEvent:
                base_handlers = self._handlers.get(DomainEvent, [])
                for handler in base_handlers:
                    try:
                        result = handler(event)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        logger.exception(
                            "Error in base event handler %s for event %s",
                            handler.__name__,
                            event_type.__name__,
                        )

    async def subscribe(self, event_type: type, handler: Callable) -> None:
        """Register a handler for a specific domain event type."""
        self._handlers[event_type].append(handler)
