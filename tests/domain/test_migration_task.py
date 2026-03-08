"""Tests for the MigrationTask entity — pure domain logic, no mocks."""

from datetime import datetime, timezone

import pytest

from domain.entities.migration_task import MigrationTask
from domain.events.migration_events import (
    MigrationTaskCompletedEvent,
    MigrationTaskFailedEvent,
    MigrationTaskStartedEvent,
)
from domain.value_objects.migration_types import MigrationTaskStatus, MigrationTaskType


def _make_task(
    *,
    status: MigrationTaskStatus = MigrationTaskStatus.PENDING,
    retry_count: int = 0,
    max_retries: int = 3,
    task_type: MigrationTaskType = MigrationTaskType.DMO_PRECHECK,
) -> MigrationTask:
    return MigrationTask(
        id="task-001",
        programme_id="prog-001",
        module="migration-orchestrator",
        task_name="DMO Pre-Migration Checks",
        description="Execute pre-migration checks",
        owner=None,
        status=status,
        depends_on=(),
        planned_start=None,
        actual_start=None,
        actual_end=None,
        duration_minutes=None,
        error_message=None,
        retry_count=retry_count,
        max_retries=max_retries,
        task_type=task_type,
        execution_params=(("check_type", "full"),),
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestStartTask:
    def test_start_task(self) -> None:
        task = _make_task()

        started = task.start()

        assert started.status == MigrationTaskStatus.IN_PROGRESS
        assert started.actual_start is not None
        assert len(started.domain_events) == 1
        event = started.domain_events[0]
        assert isinstance(event, MigrationTaskStartedEvent)
        assert event.task_id == "task-001"
        assert event.task_name == "DMO Pre-Migration Checks"
        assert event.task_type == "DMO_PRECHECK"

    def test_cannot_start_completed_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.COMPLETED)

        with pytest.raises(ValueError, match="Cannot start task"):
            task.start()

    def test_cannot_start_failed_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.FAILED)

        with pytest.raises(ValueError, match="Cannot start task"):
            task.start()

    def test_can_start_queued_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.QUEUED)

        started = task.start()

        assert started.status == MigrationTaskStatus.IN_PROGRESS


class TestCompleteTask:
    def test_complete_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.PENDING)
        started = task.start()

        completed = started.complete(duration_minutes=45)

        assert completed.status == MigrationTaskStatus.COMPLETED
        assert completed.duration_minutes == 45
        assert completed.actual_end is not None
        # Should have both start and complete events
        assert len(completed.domain_events) == 2
        assert isinstance(completed.domain_events[1], MigrationTaskCompletedEvent)
        assert completed.domain_events[1].duration_minutes == 45

    def test_cannot_complete_pending_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.PENDING)

        with pytest.raises(ValueError, match="Cannot complete task"):
            task.complete(duration_minutes=30)


class TestFailTask:
    def test_fail_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.PENDING)
        started = task.start()

        failed = started.fail(error_message="SUM phase failed with RC 12")

        assert failed.status == MigrationTaskStatus.FAILED
        assert failed.error_message == "SUM phase failed with RC 12"
        assert failed.actual_end is not None
        assert len(failed.domain_events) == 2
        assert isinstance(failed.domain_events[1], MigrationTaskFailedEvent)
        assert failed.domain_events[1].error_message == "SUM phase failed with RC 12"

    def test_cannot_fail_pending_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.PENDING)

        with pytest.raises(ValueError, match="Cannot fail task"):
            task.fail(error_message="error")


class TestRetryTask:
    def test_retry_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.PENDING)
        started = task.start()
        failed = started.fail(error_message="Transient error")

        retried = failed.retry()

        assert retried.status == MigrationTaskStatus.PENDING
        assert retried.retry_count == 1
        assert retried.actual_start is None
        assert retried.actual_end is None
        assert retried.error_message is None

    def test_retry_exceeds_max(self) -> None:
        task = _make_task(
            status=MigrationTaskStatus.PENDING,
            retry_count=0,
            max_retries=2,
        )
        started = task.start()
        failed = started.fail(error_message="error")

        # First retry works
        retried1 = failed.retry()
        assert retried1.retry_count == 1

        # Second retry works
        started2 = retried1.start()
        failed2 = started2.fail(error_message="error again")
        retried2 = failed2.retry()
        assert retried2.retry_count == 2

        # Third attempt fails — max_retries exhausted
        started3 = retried2.start()
        failed3 = started3.fail(error_message="error once more")
        with pytest.raises(ValueError, match="exhausted all 2 retries"):
            failed3.retry()

    def test_cannot_retry_pending_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.PENDING)

        with pytest.raises(ValueError, match="Cannot retry task"):
            task.retry()


class TestBlockTask:
    def test_block_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.PENDING)

        blocked = task.block(reason="Waiting for manual approval")

        assert blocked.status == MigrationTaskStatus.BLOCKED
        assert blocked.error_message == "Waiting for manual approval"

    def test_cannot_block_in_progress_task(self) -> None:
        task = _make_task(status=MigrationTaskStatus.IN_PROGRESS)

        with pytest.raises(ValueError, match="Cannot block task"):
            task.block(reason="reason")


class TestAssignOwner:
    def test_assign_owner(self) -> None:
        task = _make_task()

        assigned = task.assign_owner("john.doe@example.com")

        assert assigned.owner == "john.doe@example.com"


class TestImmutability:
    def test_task_immutability(self) -> None:
        original = _make_task()

        started = original.start()

        # Original must remain unchanged
        assert original.status == MigrationTaskStatus.PENDING
        assert original.actual_start is None
        assert original.domain_events == ()

        # Started reflects the new state
        assert started.status == MigrationTaskStatus.IN_PROGRESS
        assert started.actual_start is not None
        assert len(started.domain_events) == 1

    def test_frozen_dataclass_prevents_mutation(self) -> None:
        task = _make_task()

        with pytest.raises(AttributeError):
            task.status = MigrationTaskStatus.COMPLETED  # type: ignore[misc]
