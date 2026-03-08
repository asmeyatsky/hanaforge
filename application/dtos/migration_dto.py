"""Migration orchestrator DTOs — Pydantic models for API serialization."""

from __future__ import annotations

from pydantic import BaseModel

from domain.entities.audit_entry import AuditEntry
from domain.entities.migration_task import MigrationTask
from domain.value_objects.migration_types import AnomalyAlert


# ------------------------------------------------------------------
# Request DTOs
# ------------------------------------------------------------------


class CreateMigrationPlanRequest(BaseModel):
    """Request payload to create a migration plan for a programme."""

    approach: str
    landscape_metadata: dict = {}


# ------------------------------------------------------------------
# Response DTOs
# ------------------------------------------------------------------


class MigrationTaskResponse(BaseModel):
    """Serialisable representation of a MigrationTask entity."""

    id: str
    task_name: str
    task_type: str
    status: str
    owner: str | None = None
    depends_on: list[str]
    planned_start: str | None = None
    actual_start: str | None = None
    actual_end: str | None = None
    duration_minutes: int | None = None
    error_message: str | None = None
    retry_count: int

    @staticmethod
    def from_entity(task: MigrationTask) -> MigrationTaskResponse:
        return MigrationTaskResponse(
            id=task.id,
            task_name=task.task_name,
            task_type=task.task_type.value,
            status=task.status.value,
            owner=task.owner,
            depends_on=list(task.depends_on),
            planned_start=task.planned_start.isoformat() if task.planned_start else None,
            actual_start=task.actual_start.isoformat() if task.actual_start else None,
            actual_end=task.actual_end.isoformat() if task.actual_end else None,
            duration_minutes=task.duration_minutes,
            error_message=task.error_message,
            retry_count=task.retry_count,
        )


class MigrationPlanResponse(BaseModel):
    """Response after creating a migration plan."""

    programme_id: str
    approach: str
    total_tasks: int
    critical_path_duration_minutes: int
    tasks: list[MigrationTaskResponse]


class MigrationBatchResponse(BaseModel):
    """Response after executing a batch of migration tasks."""

    programme_id: str
    tasks_executed: int
    tasks_completed: int
    tasks_failed: int
    results: list[MigrationTaskResponse]


class MigrationStatusResponse(BaseModel):
    """Full migration status including health, critical path, and anomalies."""

    programme_id: str
    health: dict
    critical_path: dict
    tasks_summary: dict
    active_anomalies: list[dict]
    tasks: list[MigrationTaskResponse]


class AnomalyAlertResponse(BaseModel):
    """Serialisable representation of an AnomalyAlert."""

    id: str
    alert_type: str
    severity: str
    message: str
    detected_at: str
    metric_name: str | None = None
    expected_value: float | None = None
    actual_value: float | None = None
    acknowledged: bool

    @staticmethod
    def from_value_object(alert: AnomalyAlert) -> AnomalyAlertResponse:
        return AnomalyAlertResponse(
            id=alert.id,
            alert_type=alert.alert_type.value,
            severity=alert.severity.value,
            message=alert.message,
            detected_at=alert.detected_at.isoformat(),
            metric_name=alert.metric_name,
            expected_value=alert.expected_value,
            actual_value=alert.actual_value,
            acknowledged=alert.acknowledged,
        )


class AuditEntryResponse(BaseModel):
    """Serialisable representation of an AuditEntry."""

    id: str
    timestamp: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details: str
    severity: str

    @staticmethod
    def from_entity(entry: AuditEntry) -> AuditEntryResponse:
        return AuditEntryResponse(
            id=entry.id,
            timestamp=entry.timestamp.isoformat(),
            actor=entry.actor,
            action=entry.action.value,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            details=entry.details,
            severity=entry.severity.value,
        )


class AuditLogResponse(BaseModel):
    """Paginated audit log for a programme."""

    programme_id: str
    entries: list[AuditEntryResponse]
    total: int
