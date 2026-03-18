"""Event bus port — boundary for domain event publication and subscription."""

from __future__ import annotations

from typing import Callable, Protocol

from domain.events.event_base import DomainEvent


class EventBusPort(Protocol):
    async def publish(self, events: list[DomainEvent]) -> None: ...
    async def subscribe(self, event_type: type, handler: Callable) -> None: ...
