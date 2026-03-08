"""MigrationTask entity — represents a single executable step in a migration programme."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from domain.events.event_base import DomainEvent
from domain.events.migration_events import (
    MigrationTaskCompletedEvent,
    MigrationTaskFailedEvent,
    MigrationTaskStartedEvent,
)
from domain.value_objects.migration_types import MigrationTaskStatus, MigrationTaskType


@dataclass(frozen=True)
class MigrationTask:
    """A single migration task within a programme's task graph.

    Frozen dataclass — all mutations return a new instance.
    execution_params is stored as a tuple of (key, value) pairs for immutability.
    """

    id: str
    programme_id: str
    module: str
    task_name: str
    description: str
    owner: str | None
    status: MigrationTaskStatus
    depends_on: tuple[str, ...]
    planned_start: datetime | None
    actual_start: datetime | None
    actual_end: datetime | None
    duration_minutes: int | None
    error_message: str | None
    retry_count: int
    max_retries: int
    task_type: MigrationTaskType
    execution_params: tuple[tuple[str, str], ...] | None
    created_at: datetime
    domain_events: tuple[DomainEvent, ...] = ()

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def start(self) -> MigrationTask:
        """Transition task to IN_PROGRESS, recording the start time."""
        if self.status not in (MigrationTaskStatus.PENDING, MigrationTaskStatus.QUEUED):
            raise ValueError(
                f"Cannot start task in status {self.status.value}"
            )
        now = datetime.now(timezone.utc)
        event = MigrationTaskStartedEvent(
            aggregate_id=self.programme_id,
            task_id=self.id,
            task_name=self.task_name,
            task_type=self.task_type.value,
        )
        return replace(
            self,
            status=MigrationTaskStatus.IN_PROGRESS,
            actual_start=now,
            domain_events=(*self.domain_events, event),
        )

    def complete(self, duration_minutes: int) -> MigrationTask:
        """Mark task as successfully completed with its execution duration."""
        if self.status != MigrationTaskStatus.IN_PROGRESS:
            raise ValueError(
                f"Cannot complete task in status {self.status.value}"
            )
        now = datetime.now(timezone.utc)
        event = MigrationTaskCompletedEvent(
            aggregate_id=self.programme_id,
            task_id=self.id,
            task_name=self.task_name,
            duration_minutes=duration_minutes,
        )
        return replace(
            self,
            status=MigrationTaskStatus.COMPLETED,
            actual_end=now,
            duration_minutes=duration_minutes,
            domain_events=(*self.domain_events, event),
        )

    def fail(self, error_message: str) -> MigrationTask:
        """Mark task as failed with an error message."""
        if self.status != MigrationTaskStatus.IN_PROGRESS:
            raise ValueError(
                f"Cannot fail task in status {self.status.value}"
            )
        now = datetime.now(timezone.utc)
        event = MigrationTaskFailedEvent(
            aggregate_id=self.programme_id,
            task_id=self.id,
            task_name=self.task_name,
            error_message=error_message,
        )
        return replace(
            self,
            status=MigrationTaskStatus.FAILED,
            actual_end=now,
            error_message=error_message,
            domain_events=(*self.domain_events, event),
        )

    def retry(self) -> MigrationTask:
        """Reset task for retry — increments retry_count and resets to PENDING."""
        if self.status != MigrationTaskStatus.FAILED:
            raise ValueError(
                f"Cannot retry task in status {self.status.value}"
            )
        if self.retry_count >= self.max_retries:
            raise ValueError(
                f"Task has exhausted all {self.max_retries} retries"
            )
        return replace(
            self,
            status=MigrationTaskStatus.PENDING,
            retry_count=self.retry_count + 1,
            actual_start=None,
            actual_end=None,
            error_message=None,
        )

    def block(self, reason: str) -> MigrationTask:
        """Block the task with a reason description."""
        if self.status not in (
            MigrationTaskStatus.PENDING,
            MigrationTaskStatus.QUEUED,
        ):
            raise ValueError(
                f"Cannot block task in status {self.status.value}"
            )
        return replace(
            self,
            status=MigrationTaskStatus.BLOCKED,
            error_message=reason,
        )

    def assign_owner(self, owner: str) -> MigrationTask:
        """Assign an owner to the task."""
        return replace(self, owner=owner)
