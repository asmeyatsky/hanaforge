"""CutoverRunbook aggregate root — manages the cutover plan and its lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from domain.events.event_base import DomainEvent
from domain.value_objects.cutover_types import (
    CutoverTask,
    GoNoGoGate,
    RollbackPlan,
    RunbookStatus,
)


@dataclass(frozen=True)
class CutoverRunbook:
    """Immutable aggregate representing a structured cutover runbook."""

    id: str
    programme_id: str
    version: int
    name: str
    tasks: tuple[CutoverTask, ...] = ()
    go_nogo_gates: tuple[GoNoGoGate, ...] = ()
    rollback_plan: RollbackPlan = RollbackPlan()
    status: RunbookStatus = RunbookStatus.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime = None  # type: ignore[assignment]
    domain_events: tuple[DomainEvent, ...] = ()

    def __post_init__(self) -> None:
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc))

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def approve(self, approver: str) -> CutoverRunbook:
        """Mark the runbook as approved by the given approver."""
        if self.status != RunbookStatus.DRAFT:
            raise ValueError(
                f"Cannot approve runbook in status {self.status.value}; must be DRAFT"
            )
        now = datetime.now(timezone.utc)
        return replace(
            self,
            status=RunbookStatus.APPROVED,
            approved_by=approver,
            approved_at=now,
        )

    def start_execution(self) -> CutoverRunbook:
        """Transition from APPROVED to IN_EXECUTION."""
        if self.status != RunbookStatus.APPROVED:
            raise ValueError(
                f"Cannot start execution from status {self.status.value}; must be APPROVED"
            )
        return replace(self, status=RunbookStatus.IN_EXECUTION)

    def increment_version(self) -> CutoverRunbook:
        """Bump the version number and reset back to DRAFT."""
        return replace(
            self,
            version=self.version + 1,
            status=RunbookStatus.DRAFT,
            approved_by=None,
            approved_at=None,
        )

    def add_task(self, task: CutoverTask) -> CutoverRunbook:
        """Append a task to the runbook (returns a new instance)."""
        return replace(self, tasks=(*self.tasks, task))

    def complete(self) -> CutoverRunbook:
        """Mark runbook as completed."""
        if self.status != RunbookStatus.IN_EXECUTION:
            raise ValueError(
                f"Cannot complete runbook in status {self.status.value}; must be IN_EXECUTION"
            )
        return replace(self, status=RunbookStatus.COMPLETED)

    def abort(self) -> CutoverRunbook:
        """Mark runbook as aborted."""
        if self.status not in (RunbookStatus.IN_EXECUTION, RunbookStatus.APPROVED):
            raise ValueError(
                f"Cannot abort runbook in status {self.status.value}"
            )
        return replace(self, status=RunbookStatus.ABORTED)
