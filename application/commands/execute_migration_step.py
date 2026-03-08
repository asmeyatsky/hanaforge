"""ExecuteMigrationStepUseCase — executes a single migration task with anomaly detection."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

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

from application.dtos.migration_dto import MigrationTaskResponse


class ExecuteMigrationStepUseCase:
    """Single-responsibility use case: execute one migration task, detect anomalies, audit."""

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

    async def execute(self, task_id: str) -> MigrationTaskResponse:
        """Execute a single migration step.

        1. Get task, validate it's ready (dependencies complete)
        2. Start task, save
        3. Execute via MigrationExecutorPort
        4. Check for anomalies
        5. Complete or fail task
        6. Create audit entry
        7. Publish events
        """
        now = datetime.now(timezone.utc)

        # 1. Get and validate task
        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Task {task_id!r} not found")

        # Validate dependencies are complete
        if task.depends_on:
            for dep_id in task.depends_on:
                dep_task = await self._task_repo.get_by_id(dep_id)
                if dep_task is None:
                    raise ValueError(f"Dependency task {dep_id!r} not found")
                if dep_task.status != MigrationTaskStatus.COMPLETED:
                    raise ValueError(
                        f"Dependency '{dep_task.task_name}' ({dep_id}) "
                        f"is not complete (status: {dep_task.status.value})"
                    )

        # 2. Start task
        task = task.start()
        await self._task_repo.save(task)

        # Audit: task started
        start_audit = AuditEntry(
            id=str(uuid.uuid4()),
            programme_id=task.programme_id,
            timestamp=now,
            actor="system",
            action=AuditAction.TASK_STARTED,
            resource_type="MigrationTask",
            resource_id=task.id,
            details=f"Started task '{task.task_name}'",
            metadata=(("task_type", task.task_type.value),),
            severity=AuditSeverity.INFO,
        )
        await self._audit_repo.save(start_audit)

        # 3. Execute via infrastructure adapter
        try:
            result = await self._executor.execute_task(task)
            duration = result.get("duration_minutes", 1)
            execution_metrics = result.get("metrics", {})

            # 4. Check for anomalies
            anomalies = self._anomaly_service.detect_anomalies(
                task, execution_metrics
            )
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

            # 5. Complete task
            task = task.complete(duration_minutes=duration)
            await self._task_repo.save(task)

            # 6. Audit: task completed
            complete_audit = AuditEntry(
                id=str(uuid.uuid4()),
                programme_id=task.programme_id,
                timestamp=datetime.now(timezone.utc),
                actor="system",
                action=AuditAction.TASK_COMPLETED,
                resource_type="MigrationTask",
                resource_id=task.id,
                details=(
                    f"Completed task '{task.task_name}' "
                    f"in {duration} minutes"
                ),
                metadata=(
                    ("task_type", task.task_type.value),
                    ("duration_minutes", str(duration)),
                ),
                severity=AuditSeverity.INFO,
            )
            await self._audit_repo.save(complete_audit)

        except Exception as exc:
            # 5. Fail task
            error_msg = str(exc)
            task = task.fail(error_message=error_msg)
            await self._task_repo.save(task)

            # 6. Audit: task failed
            fail_audit = AuditEntry(
                id=str(uuid.uuid4()),
                programme_id=task.programme_id,
                timestamp=datetime.now(timezone.utc),
                actor="system",
                action=AuditAction.TASK_FAILED,
                resource_type="MigrationTask",
                resource_id=task.id,
                details=f"Failed task '{task.task_name}': {error_msg}",
                metadata=(
                    ("task_type", task.task_type.value),
                    ("error", error_msg),
                ),
                severity=AuditSeverity.ERROR,
            )
            await self._audit_repo.save(fail_audit)

        # 7. Publish domain events accumulated on the task
        if task.domain_events:
            await self._event_bus.publish(list(task.domain_events))

        return MigrationTaskResponse.from_entity(task)
