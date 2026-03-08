"""Cutover Commander domain events — emitted during cutover lifecycle transitions."""

from __future__ import annotations

from dataclasses import dataclass

from domain.events.event_base import DomainEvent


@dataclass(frozen=True)
class RunbookGeneratedEvent(DomainEvent):
    programme_id: str = ""
    runbook_id: str = ""
    task_count: int = 0


@dataclass(frozen=True)
class RunbookApprovedEvent(DomainEvent):
    programme_id: str = ""
    runbook_id: str = ""
    approved_by: str = ""


@dataclass(frozen=True)
class CutoverStartedEvent(DomainEvent):
    programme_id: str = ""
    execution_id: str = ""
    planned_duration_minutes: int = 0


@dataclass(frozen=True)
class GoNoGoGateEvaluatedEvent(DomainEvent):
    programme_id: str = ""
    gate_name: str = ""
    status: str = ""


@dataclass(frozen=True)
class CutoverCompletedEvent(DomainEvent):
    programme_id: str = ""
    execution_id: str = ""
    total_duration_minutes: int = 0
    deviations_count: int = 0


@dataclass(frozen=True)
class CutoverAbortedEvent(DomainEvent):
    programme_id: str = ""
    execution_id: str = ""
    reason: str = ""


@dataclass(frozen=True)
class HypercareStartedEvent(DomainEvent):
    programme_id: str = ""
    duration_days: int = 0


@dataclass(frozen=True)
class HypercareIncidentEvent(DomainEvent):
    programme_id: str = ""
    severity: str = ""
    description: str = ""


@dataclass(frozen=True)
class KnowledgeCapturedEvent(DomainEvent):
    programme_id: str = ""
    title: str = ""
    category: str = ""


@dataclass(frozen=True)
class LessonsLearnedGeneratedEvent(DomainEvent):
    programme_id: str = ""
    entry_count: int = 0
