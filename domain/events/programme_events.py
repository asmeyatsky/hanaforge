"""Programme lifecycle domain events."""

from __future__ import annotations

from dataclasses import dataclass

from domain.events.event_base import DomainEvent


@dataclass(frozen=True)
class ProgrammeCreatedEvent(DomainEvent):
    programme_name: str = ""
    customer_id: str = ""


@dataclass(frozen=True)
class DiscoveryStartedEvent(DomainEvent):
    landscape_id: str = ""


@dataclass(frozen=True)
class DiscoveryCompletedEvent(DomainEvent):
    complexity_score: int = 0


@dataclass(frozen=True)
class AnalysisStartedEvent(DomainEvent):
    object_count: int = 0


@dataclass(frozen=True)
class AnalysisCompletedEvent(DomainEvent):
    compatible_count: int = 0
    incompatible_count: int = 0
