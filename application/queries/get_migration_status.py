"""GetMigrationStatusQuery — retrieves full migration status with health, critical path, anomalies."""

from __future__ import annotations

from application.dtos.migration_dto import (
    AnomalyAlertResponse,
    MigrationStatusResponse,
    MigrationTaskResponse,
)
from domain.ports.migration_ports import (
    AnomalyRepositoryPort,
    MigrationTaskRepositoryPort,
)
from domain.services.task_graph_service import TaskGraphService


class GetMigrationStatusQuery:
    """Read-only query: returns task graph status, critical path, health, and active anomalies."""

    def __init__(
        self,
        task_repo: MigrationTaskRepositoryPort,
        anomaly_repo: AnomalyRepositoryPort,
        task_graph_service: TaskGraphService,
    ) -> None:
        self._task_repo = task_repo
        self._anomaly_repo = anomaly_repo
        self._task_graph_service = task_graph_service

    async def execute(self, programme_id: str) -> MigrationStatusResponse:
        """Compute and return full migration status."""
        tasks = await self._task_repo.list_by_programme(programme_id)
        anomalies = await self._anomaly_repo.list_active(programme_id)

        # Critical path
        critical_path = self._task_graph_service.calculate_critical_path(tasks)

        # Health
        health = self._task_graph_service.calculate_migration_health(tasks, anomalies)

        # Build response
        task_responses = [MigrationTaskResponse.from_entity(t) for t in tasks]
        anomaly_responses = [AnomalyAlertResponse.from_value_object(a) for a in anomalies]

        return MigrationStatusResponse(
            programme_id=programme_id,
            health={
                "overall_status": health.overall_status,
                "tasks_completed": health.tasks_completed,
                "tasks_in_progress": health.tasks_in_progress,
                "tasks_pending": health.tasks_pending,
                "tasks_failed": health.tasks_failed,
                "active_anomalies": health.active_anomalies,
                "critical_path_deviation_minutes": health.critical_path_deviation_minutes,
                "last_updated": health.last_updated.isoformat(),
            },
            critical_path={
                "total_duration_minutes": critical_path.total_duration_minutes,
                "critical_tasks": list(critical_path.critical_tasks),
                "slack_per_task": [
                    {"task_id": tid, "slack_minutes": slack} for tid, slack in critical_path.slack_per_task
                ],
            },
            tasks_summary={
                "total": len(tasks),
                "completed": health.tasks_completed,
                "in_progress": health.tasks_in_progress,
                "pending": health.tasks_pending,
                "failed": health.tasks_failed,
            },
            active_anomalies=[a.model_dump() for a in anomaly_responses],
            tasks=task_responses,
        )
