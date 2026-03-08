"""Analysis and remediation domain events."""

from __future__ import annotations

from dataclasses import dataclass

from domain.events.event_base import DomainEvent


@dataclass(frozen=True)
class ObjectAnalysedEvent(DomainEvent):
    object_name: str = ""
    compatibility_status: str = ""


@dataclass(frozen=True)
class RemediationGeneratedEvent(DomainEvent):
    object_id: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class RemediationReviewedEvent(DomainEvent):
    object_id: str = ""
    approved: bool = False
    reviewer: str = ""
