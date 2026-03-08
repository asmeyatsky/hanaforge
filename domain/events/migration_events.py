"""Migration orchestrator domain events."""

from __future__ import annotations

from dataclasses import dataclass

from domain.events.event_base import DomainEvent


@dataclass(frozen=True)
class MigrationStartedEvent(DomainEvent):
    programme_id: str = ""
    approach: str = ""
    total_tasks: int = 0


@dataclass(frozen=True)
class MigrationTaskStartedEvent(DomainEvent):
    task_id: str = ""
    task_name: str = ""
    task_type: str = ""


@dataclass(frozen=True)
class MigrationTaskCompletedEvent(DomainEvent):
    task_id: str = ""
    task_name: str = ""
    duration_minutes: int = 0


@dataclass(frozen=True)
class MigrationTaskFailedEvent(DomainEvent):
    task_id: str = ""
    task_name: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class AnomalyDetectedEvent(DomainEvent):
    programme_id: str = ""
    alert_type: str = ""
    severity: str = ""
    message: str = ""


@dataclass(frozen=True)
class MigrationCompletedEvent(DomainEvent):
    programme_id: str = ""
    total_duration_minutes: int = 0
    tasks_completed: int = 0


@dataclass(frozen=True)
class MigrationPausedEvent(DomainEvent):
    programme_id: str = ""
    reason: str = ""
