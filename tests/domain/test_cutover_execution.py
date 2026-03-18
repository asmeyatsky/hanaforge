"""Tests for CutoverExecution aggregate — pure domain logic, no mocks."""

from datetime import datetime, timezone

import pytest

from domain.entities.cutover_execution import CutoverExecution
from domain.value_objects.cutover_types import (
    CutoverIssue,
    ExecutionDeviation,
    ExecutionStatus,
    TaskExecution,
)


def _make_execution(
    *,
    status: ExecutionStatus = ExecutionStatus.NOT_STARTED,
    tasks: tuple[TaskExecution, ...] | None = None,
) -> CutoverExecution:
    if tasks is None:
        tasks = (
            TaskExecution(task_id="T-001", task_name="Backup database"),
            TaskExecution(task_id="T-002", task_name="Lock users"),
            TaskExecution(task_id="T-003", task_name="Run migration"),
        )
    return CutoverExecution(
        id="exec-001",
        runbook_id="rb-001",
        programme_id="prog-001",
        started_at=datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
        status=status,
        task_statuses=tasks,
        planned_duration_minutes=480,
    )


class TestStartCutoverExecution:
    def test_start_cutover_execution(self) -> None:
        execution = _make_execution()
        assert execution.status == ExecutionStatus.NOT_STARTED

        started = execution.start()

        assert started.status == ExecutionStatus.IN_PROGRESS
        # Original unchanged
        assert execution.status == ExecutionStatus.NOT_STARTED

    def test_cannot_start_already_started(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)
        with pytest.raises(ValueError, match="Cannot start"):
            execution.start()


class TestUpdateTaskStatus:
    def test_update_task_status(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)

        updated = execution.update_task(
            task_id="T-001",
            status="IN_PROGRESS",
            executor="basis_admin",
        )

        task = next(t for t in updated.task_statuses if t.task_id == "T-001")
        assert task.status == "IN_PROGRESS"
        assert task.executor == "basis_admin"
        assert task.started_at is not None

    def test_complete_task(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)

        # Start then complete
        started = execution.update_task(task_id="T-001", status="IN_PROGRESS")
        completed = started.update_task(
            task_id="T-001",
            status="COMPLETED",
            notes="Backup verified",
        )

        task = next(t for t in completed.task_statuses if t.task_id == "T-001")
        assert task.status == "COMPLETED"
        assert task.completed_at is not None
        assert task.notes == "Backup verified"

    def test_update_nonexistent_task_raises(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)
        with pytest.raises(ValueError, match="not found"):
            execution.update_task(task_id="T-999", status="IN_PROGRESS")


class TestRecordDeviation:
    def test_record_deviation(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)
        now = datetime.now(timezone.utc)

        deviation = ExecutionDeviation(
            task_id="T-001",
            deviation_type="DELAY",
            planned_value="120 minutes",
            actual_value="180 minutes",
            impact="60 minute delay on critical path",
            recorded_at=now,
        )

        updated = execution.record_deviation(deviation)

        assert len(updated.deviations) == 1
        assert updated.deviations[0].task_id == "T-001"
        assert updated.deviations[0].deviation_type == "DELAY"
        # Original unchanged
        assert len(execution.deviations) == 0

    def test_multiple_deviations(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)
        now = datetime.now(timezone.utc)

        d1 = ExecutionDeviation(
            task_id="T-001",
            deviation_type="DELAY",
            planned_value="60",
            actual_value="90",
            impact="Minor",
            recorded_at=now,
        )
        d2 = ExecutionDeviation(
            task_id="T-002",
            deviation_type="SKIP",
            planned_value="Execute",
            actual_value="Skipped",
            impact="None",
            recorded_at=now,
        )

        updated = execution.record_deviation(d1).record_deviation(d2)
        assert len(updated.deviations) == 2


class TestLogIssue:
    def test_log_issue(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)
        now = datetime.now(timezone.utc)

        issue = CutoverIssue(
            id="ISS-001",
            severity="HIGH",
            description="RFC destination timeout during migration",
            affected_task_id="T-003",
            raised_at=now,
        )

        updated = execution.log_issue(issue)

        assert len(updated.issues) == 1
        assert updated.issues[0].severity == "HIGH"
        assert updated.issues[0].affected_task_id == "T-003"
        # Original unchanged
        assert len(execution.issues) == 0


class TestCompleteExecution:
    def test_complete_execution(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)

        completed = execution.complete()

        assert completed.status == ExecutionStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.elapsed_minutes >= 0

    def test_cannot_complete_not_started(self) -> None:
        execution = _make_execution(status=ExecutionStatus.NOT_STARTED)
        with pytest.raises(ValueError, match="Cannot complete"):
            execution.complete()


class TestAbortExecution:
    def test_abort_execution(self) -> None:
        execution = _make_execution(status=ExecutionStatus.IN_PROGRESS)

        aborted = execution.abort(reason="Critical data mismatch detected")

        assert aborted.status == ExecutionStatus.ABORTED
        assert aborted.completed_at is not None
        # Should auto-log a CRITICAL issue
        assert len(aborted.issues) == 1
        assert aborted.issues[0].severity == "CRITICAL"
        assert "Critical data mismatch" in aborted.issues[0].description

    def test_cannot_abort_completed(self) -> None:
        execution = _make_execution(status=ExecutionStatus.COMPLETED)
        with pytest.raises(ValueError, match="Cannot abort"):
            execution.abort(reason="Too late")


class TestImmutability:
    def test_execution_is_immutable(self) -> None:
        original = _make_execution(status=ExecutionStatus.IN_PROGRESS)

        updated = original.update_task(task_id="T-001", status="IN_PROGRESS")

        # Original must remain unchanged
        task_orig = next(t for t in original.task_statuses if t.task_id == "T-001")
        task_updated = next(t for t in updated.task_statuses if t.task_id == "T-001")
        assert task_orig.status == "NOT_STARTED"
        assert task_updated.status == "IN_PROGRESS"
