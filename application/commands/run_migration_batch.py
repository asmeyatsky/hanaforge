"""RunMigrationBatchUseCase — executes all ready migration tasks in parallel batches."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from application.dtos.migration_dto import MigrationBatchResponse, MigrationTaskResponse
from domain.entities.audit_entry import AuditEntry
from domain.events.migration_events import AnomalyDetectedEvent
from domain.ports.event_bus_ports import EventBusPort
from domain.ports.migration_ports import (
    AnomalyRepositoryPort,
    AuditRepositoryPort,
    MigrationExecutorPort,
    MigrationTaskRepositoryPort,
)
from domain.services.anomaly_detection_service import AnomalyDetectionService
from domain.value_objects.migration_types import (
    AuditAction,
    AuditSeverity,
    MigrationTaskStatus,
)

_MAX_CONCURRENCY = 5


class RunMigrationBatchUseCase:
    """Execute all ready migration tasks concurrently, respecting dependency order.

    Uses asyncio.gather with a Semaphore to limit concurrency to 5 simultaneous tasks.
    Continues until no more tasks are ready or a failure occurs.
    """

    def __init__(
        self,
        task_repo: MigrationTaskRepositoryPort,
        audit_repo: AuditRepositoryPort,
        anomaly_repo: AnomalyRepositoryPort,
        executor: MigrationExecutorPort,
        anomaly_service: AnomalyDetectionService,
        event_bus: EventBusPort,
    ) -> None:
        self._task_repo = task_repo
        self._audit_repo = audit_repo
        self._anomaly_repo = anomaly_repo
        self._executor = executor
        self._anomaly_service = anomaly_service
        self._event_bus = event_bus

    async def execute(self, programme_id: str) -> MigrationBatchResponse:
        """Run ready tasks in parallel batches until none remain or failure stops execution."""
        semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
        all_results: list[MigrationTaskResponse] = []
        total_completed = 0
        total_failed = 0
        has_failure = False

        while not has_failure:
            # Get all tasks for the programme
            all_tasks = await self._task_repo.list_by_programme(programme_id)
            completed_ids = {t.id for t in all_tasks if t.status == MigrationTaskStatus.COMPLETED}

            # Find ready tasks — PENDING with all dependencies satisfied
            ready_tasks = [
                t
                for t in all_tasks
                if t.status == MigrationTaskStatus.PENDING and all(dep_id in completed_ids for dep_id in t.depends_on)
            ]

            if not ready_tasks:
                break

            # Execute ready tasks with concurrency limit
            async def _run_one(task_id: str) -> MigrationTaskResponse:
                async with semaphore:
                    return await self._execute_single_task(task_id)

            batch_results = await asyncio.gather(
                *[_run_one(t.id) for t in ready_tasks],
                return_exceptions=True,
            )

            for result in batch_results:
                if isinstance(result, Exception):
                    # An unexpected exception during execution
                    has_failure = True
                    total_failed += 1
                elif isinstance(result, MigrationTaskResponse):
                    all_results.append(result)
                    if result.status == MigrationTaskStatus.COMPLETED.value:
                        total_completed += 1
                    elif result.status == MigrationTaskStatus.FAILED.value:
                        total_failed += 1
                        has_failure = True

        return MigrationBatchResponse(
            programme_id=programme_id,
            tasks_executed=len(all_results),
            tasks_completed=total_completed,
            tasks_failed=total_failed,
            results=all_results,
        )

    async def _execute_single_task(self, task_id: str) -> MigrationTaskResponse:
        """Execute a single task — mirrors ExecuteMigrationStepUseCase logic."""
        now = datetime.now(timezone.utc)

        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Task {task_id!r} not found")

        # Start task
        task = task.start()
        await self._task_repo.save(task)

        start_audit = AuditEntry(
            id=str(uuid.uuid4()),
            programme_id=task.programme_id,
            timestamp=now,
            actor="system",
            action=AuditAction.TASK_STARTED,
            resource_type="MigrationTask",
            resource_id=task.id,
            details=f"Started task '{task.task_name}' (batch mode)",
            metadata=(("task_type", task.task_type.value),),
            severity=AuditSeverity.INFO,
        )
        await self._audit_repo.save(start_audit)

        try:
            result = await self._executor.execute_task(task)
            duration = result.get("duration_minutes", 1)
            execution_metrics = result.get("metrics", {})

            # Check anomalies
            anomalies = self._anomaly_service.detect_anomalies(task, execution_metrics)
            for anomaly in anomalies:
                await self._anomaly_repo.save(anomaly)
                anomaly_event = AnomalyDetectedEvent(
                    aggregate_id=task.programme_id,
                    programme_id=task.programme_id,
                    alert_type=anomaly.alert_type.value,
                    severity=anomaly.severity.value,
                    message=anomaly.message,
                )
                await self._event_bus.publish([anomaly_event])

            # Complete
            task = task.complete(duration_minutes=duration)
            await self._task_repo.save(task)

            complete_audit = AuditEntry(
                id=str(uuid.uuid4()),
                programme_id=task.programme_id,
                timestamp=datetime.now(timezone.utc),
                actor="system",
                action=AuditAction.TASK_COMPLETED,
                resource_type="MigrationTask",
                resource_id=task.id,
                details=f"Completed task '{task.task_name}' in {duration}min (batch mode)",
                metadata=(
                    ("task_type", task.task_type.value),
                    ("duration_minutes", str(duration)),
                ),
                severity=AuditSeverity.INFO,
            )
            await self._audit_repo.save(complete_audit)

        except Exception as exc:
            error_msg = str(exc)
            task = task.fail(error_message=error_msg)
            await self._task_repo.save(task)

            fail_audit = AuditEntry(
                id=str(uuid.uuid4()),
                programme_id=task.programme_id,
                timestamp=datetime.now(timezone.utc),
                actor="system",
                action=AuditAction.TASK_FAILED,
                resource_type="MigrationTask",
                resource_id=task.id,
                details=f"Failed task '{task.task_name}': {error_msg} (batch mode)",
                metadata=(
                    ("task_type", task.task_type.value),
                    ("error", error_msg),
                ),
                severity=AuditSeverity.ERROR,
            )
            await self._audit_repo.save(fail_audit)

        # Publish accumulated domain events
        if task.domain_events:
            await self._event_bus.publish(list(task.domain_events))

        return MigrationTaskResponse.from_entity(task)
