"""CutoverExecution aggregate — tracks real-time cutover progress, deviations, and issues."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from domain.events.event_base import DomainEvent
from domain.value_objects.cutover_types import (
    CutoverIssue,
    ExecutionDeviation,
    ExecutionStatus,
    TaskExecution,
)


@dataclass(frozen=True)
class CutoverExecution:
    """Immutable aggregate tracking the execution of a cutover runbook."""

    id: str
    runbook_id: str
    programme_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    task_statuses: tuple[TaskExecution, ...] = ()
    deviations: tuple[ExecutionDeviation, ...] = ()
    issues: tuple[CutoverIssue, ...] = ()
    elapsed_minutes: int = 0
    planned_duration_minutes: int = 0
    domain_events: tuple[DomainEvent, ...] = ()

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def update_task(
        self,
        task_id: str,
        status: str,
        notes: str | None = None,
        executor: str | None = None,
    ) -> CutoverExecution:
        """Update the status of a specific task in the execution tracker."""
        now = datetime.now(timezone.utc)
        updated_statuses: list[TaskExecution] = []
        found = False

        for ts in self.task_statuses:
            if ts.task_id == task_id:
                found = True
                started = ts.started_at or (now if status == "IN_PROGRESS" else None)
                completed = now if status in ("COMPLETED", "SKIPPED", "FAILED") else None
                duration = None
                if completed and started:
                    duration = int((completed - started).total_seconds() / 60)
                updated_statuses.append(
                    TaskExecution(
                        task_id=ts.task_id,
                        task_name=ts.task_name,
                        status=status,
                        started_at=started,
                        completed_at=completed,
                        actual_duration_minutes=duration,
                        notes=notes or ts.notes,
                        executor=executor or ts.executor,
                    )
                )
            else:
                updated_statuses.append(ts)

        if not found:
            raise ValueError(f"Task {task_id} not found in execution")

        # Recalculate elapsed time
        elapsed = int((now - self.started_at).total_seconds() / 60)

        return replace(
            self,
            task_statuses=tuple(updated_statuses),
            elapsed_minutes=elapsed,
        )

    def record_deviation(self, deviation: ExecutionDeviation) -> CutoverExecution:
        """Append a deviation record to the execution."""
        return replace(self, deviations=(*self.deviations, deviation))

    def log_issue(self, issue: CutoverIssue) -> CutoverExecution:
        """Log a new issue discovered during cutover."""
        return replace(self, issues=(*self.issues, issue))

    def complete(self) -> CutoverExecution:
        """Mark the cutover execution as completed."""
        if self.status != ExecutionStatus.IN_PROGRESS:
            raise ValueError(
                f"Cannot complete execution in status {self.status.value}; "
                "must be IN_PROGRESS"
            )
        now = datetime.now(timezone.utc)
        elapsed = int((now - self.started_at).total_seconds() / 60)
        return replace(
            self,
            status=ExecutionStatus.COMPLETED,
            completed_at=now,
            elapsed_minutes=elapsed,
        )

    def abort(self, reason: str) -> CutoverExecution:
        """Abort the cutover execution with a reason."""
        if self.status not in (ExecutionStatus.IN_PROGRESS, ExecutionStatus.PAUSED):
            raise ValueError(
                f"Cannot abort execution in status {self.status.value}"
            )
        now = datetime.now(timezone.utc)
        elapsed = int((now - self.started_at).total_seconds() / 60)
        issue = CutoverIssue(
            id=f"ABORT-{self.id}",
            severity="CRITICAL",
            description=f"Cutover aborted: {reason}",
            raised_at=now,
        )
        return replace(
            self,
            status=ExecutionStatus.ABORTED,
            completed_at=now,
            elapsed_minutes=elapsed,
            issues=(*self.issues, issue),
        )

    def start(self) -> CutoverExecution:
        """Transition from NOT_STARTED to IN_PROGRESS."""
        if self.status != ExecutionStatus.NOT_STARTED:
            raise ValueError(
                f"Cannot start execution in status {self.status.value}; "
                "must be NOT_STARTED"
            )
        return replace(self, status=ExecutionStatus.IN_PROGRESS)
