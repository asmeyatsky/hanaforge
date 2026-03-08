"""CreateMigrationPlanUseCase — builds the full task DAG for a migration programme."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.entities.audit_entry import AuditEntry
from domain.events.migration_events import MigrationStartedEvent
from domain.ports.event_bus_ports import EventBusPort
from domain.ports.migration_ports import AuditRepositoryPort, MigrationTaskRepositoryPort
from domain.services.task_graph_service import TaskGraphService
from domain.value_objects.migration_approach import MigrationApproach
from domain.value_objects.migration_types import AuditAction, AuditSeverity

from application.dtos.migration_dto import (
    CreateMigrationPlanRequest,
    MigrationPlanResponse,
    MigrationTaskResponse,
)


class CreateMigrationPlanUseCase:
    """Single-responsibility use case: generate and persist a migration task graph."""

    def __init__(
        self,
        programme_repo: object,  # ProgrammeRepositoryPort — used for validation
        task_repo: MigrationTaskRepositoryPort,
        audit_repo: AuditRepositoryPort,
        task_graph_service: TaskGraphService,
        event_bus: EventBusPort,
    ) -> None:
        self._programme_repo = programme_repo
        self._task_repo = task_repo
        self._audit_repo = audit_repo
        self._task_graph_service = task_graph_service
        self._event_bus = event_bus

    async def execute(
        self,
        programme_id: str,
        request: CreateMigrationPlanRequest,
    ) -> MigrationPlanResponse:
        """Build the task graph, compute critical path, persist, and publish events."""

        # 1. Parse approach
        approach = MigrationApproach(request.approach)

        # 2. Build task graph
        tasks = self._task_graph_service.build_task_graph(
            programme_id=programme_id,
            approach=approach,
            landscape_metadata=request.landscape_metadata,
        )

        # 3. Calculate critical path
        critical_path = self._task_graph_service.calculate_critical_path(tasks)

        # 4. Persist all tasks in batch
        await self._task_repo.save_batch(tasks)

        # 5. Create audit entries for each task
        now = datetime.now(timezone.utc)
        for task in tasks:
            audit_entry = AuditEntry(
                id=str(uuid.uuid4()),
                programme_id=programme_id,
                timestamp=now,
                actor="system",
                action=AuditAction.TASK_CREATED,
                resource_type="MigrationTask",
                resource_id=task.id,
                details=f"Created task '{task.task_name}' ({task.task_type.value})",
                metadata=(
                    ("approach", approach.value),
                    ("task_type", task.task_type.value),
                ),
                severity=AuditSeverity.INFO,
            )
            await self._audit_repo.save(audit_entry)

        # 6. Audit entry for migration start
        migration_audit = AuditEntry(
            id=str(uuid.uuid4()),
            programme_id=programme_id,
            timestamp=now,
            actor="system",
            action=AuditAction.MIGRATION_STARTED,
            resource_type="Programme",
            resource_id=programme_id,
            details=(
                f"Migration plan created with {len(tasks)} tasks "
                f"using {approach.value} approach. "
                f"Critical path: {critical_path.total_duration_minutes}min"
            ),
            metadata=(
                ("approach", approach.value),
                ("total_tasks", str(len(tasks))),
                ("critical_path_minutes", str(critical_path.total_duration_minutes)),
            ),
            severity=AuditSeverity.INFO,
        )
        await self._audit_repo.save(migration_audit)

        # 7. Publish MigrationStartedEvent
        event = MigrationStartedEvent(
            aggregate_id=programme_id,
            programme_id=programme_id,
            approach=approach.value,
            total_tasks=len(tasks),
        )
        await self._event_bus.publish([event])

        # 8. Build response
        task_responses = [MigrationTaskResponse.from_entity(t) for t in tasks]

        return MigrationPlanResponse(
            programme_id=programme_id,
            approach=approach.value,
            total_tasks=len(tasks),
            critical_path_duration_minutes=critical_path.total_duration_minutes,
            tasks=task_responses,
        )
