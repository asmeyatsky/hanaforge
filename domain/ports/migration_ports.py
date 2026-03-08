"""Migration orchestrator ports — async boundaries for migration persistence and execution."""

from __future__ import annotations

from typing import Protocol

from domain.entities.audit_entry import AuditEntry
from domain.entities.migration_task import MigrationTask
from domain.value_objects.migration_types import (
    AnomalyAlert,
    MigrationTaskStatus,
)


class MigrationTaskRepositoryPort(Protocol):
    """Persistence boundary for MigrationTask aggregates."""

    async def save(self, task: MigrationTask) -> None: ...
    async def save_batch(self, tasks: list[MigrationTask]) -> None: ...
    async def get_by_id(self, id: str) -> MigrationTask | None: ...
    async def list_by_programme(self, programme_id: str) -> list[MigrationTask]: ...
    async def get_pending_tasks(self, programme_id: str) -> list[MigrationTask]: ...
    async def update_status(
        self, task_id: str, status: MigrationTaskStatus
    ) -> None: ...


class AuditRepositoryPort(Protocol):
    """Persistence boundary for AuditEntry records."""

    async def save(self, entry: AuditEntry) -> None: ...
    async def list_by_programme(
        self, programme_id: str, limit: int = 100
    ) -> list[AuditEntry]: ...
    async def list_by_resource(
        self, resource_type: str, resource_id: str
    ) -> list[AuditEntry]: ...


class AnomalyRepositoryPort(Protocol):
    """Persistence boundary for AnomalyAlert records."""

    async def save(self, alert: AnomalyAlert) -> None: ...
    async def list_active(self, programme_id: str) -> list[AnomalyAlert]: ...
    async def acknowledge(self, alert_id: str) -> None: ...


class MigrationExecutorPort(Protocol):
    """Infrastructure boundary for executing migration tasks against SAP systems."""

    async def execute_task(self, task: MigrationTask) -> dict: ...
    async def check_system_health(self, connection_params: dict) -> dict: ...


class AnomalyDetectionPort(Protocol):
    """AI or rule-based anomaly detection boundary."""

    async def analyze_metrics(
        self, programme_id: str, metrics: dict
    ) -> list[AnomalyAlert]: ...
