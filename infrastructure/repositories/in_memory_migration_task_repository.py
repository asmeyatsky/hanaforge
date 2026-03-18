"""InMemoryMigrationTaskRepository — dev-mode in-memory implementation of MigrationTaskRepositoryPort."""

from __future__ import annotations

from datetime import datetime

from domain.entities.migration_task import MigrationTask
from domain.value_objects.migration_types import MigrationTaskStatus, MigrationTaskType


class InMemoryMigrationTaskRepository:
    """Implements MigrationTaskRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(task: MigrationTask) -> dict:
        return {
            "id": task.id,
            "programme_id": task.programme_id,
            "module": task.module,
            "task_name": task.task_name,
            "description": task.description,
            "owner": task.owner,
            "status": task.status.value,
            "depends_on": list(task.depends_on),
            "planned_start": task.planned_start.isoformat() if task.planned_start else None,
            "actual_start": task.actual_start.isoformat() if task.actual_start else None,
            "actual_end": task.actual_end.isoformat() if task.actual_end else None,
            "duration_minutes": task.duration_minutes,
            "error_message": task.error_message,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "task_type": task.task_type.value,
            "execution_params": list(task.execution_params) if task.execution_params else None,
            "created_at": task.created_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict) -> MigrationTask:
        return MigrationTask(
            id=data["id"],
            programme_id=data["programme_id"],
            module=data["module"],
            task_name=data["task_name"],
            description=data["description"],
            owner=data["owner"],
            status=MigrationTaskStatus(data["status"]),
            depends_on=tuple(data["depends_on"]),
            planned_start=(
                datetime.fromisoformat(data["planned_start"])
                if data["planned_start"]
                else None
            ),
            actual_start=(
                datetime.fromisoformat(data["actual_start"])
                if data["actual_start"]
                else None
            ),
            actual_end=(
                datetime.fromisoformat(data["actual_end"])
                if data["actual_end"]
                else None
            ),
            duration_minutes=data["duration_minutes"],
            error_message=data["error_message"],
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            task_type=MigrationTaskType(data["task_type"]),
            execution_params=(
                tuple(tuple(pair) for pair in data["execution_params"])
                if data["execution_params"]
                else None
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, task: MigrationTask) -> None:
        self._store[task.id] = self._to_dict(task)

    async def save_batch(self, tasks: list[MigrationTask]) -> None:
        for task in tasks:
            self._store[task.id] = self._to_dict(task)

    async def get_by_id(self, id: str) -> MigrationTask | None:
        data = self._store.get(id)
        if data is None:
            return None
        return self._from_dict(data)

    async def list_by_programme(self, programme_id: str) -> list[MigrationTask]:
        return [
            self._from_dict(data)
            for data in self._store.values()
            if data["programme_id"] == programme_id
        ]

    async def get_pending_tasks(self, programme_id: str) -> list[MigrationTask]:
        return [
            self._from_dict(data)
            for data in self._store.values()
            if data["programme_id"] == programme_id
            and data["status"] == MigrationTaskStatus.PENDING.value
        ]

    async def update_status(
        self, task_id: str, status: MigrationTaskStatus
    ) -> None:
        data = self._store.get(task_id)
        if data is not None:
            data["status"] = status.value
