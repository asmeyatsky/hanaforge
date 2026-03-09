"""Firestore-backed MigrationTaskRepository — production implementation for M06."""

from __future__ import annotations

from datetime import datetime

from domain.entities.migration_task import MigrationTask
from domain.value_objects.migration_types import MigrationTaskStatus, MigrationTaskType
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "migration_tasks"


class FirestoreMigrationTaskRepository(FirestoreBase):
    """Implements MigrationTaskRepositoryPort using Firestore."""

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
            planned_start=datetime.fromisoformat(data["planned_start"]) if data["planned_start"] else None,
            actual_start=datetime.fromisoformat(data["actual_start"]) if data["actual_start"] else None,
            actual_end=datetime.fromisoformat(data["actual_end"]) if data["actual_end"] else None,
            duration_minutes=data["duration_minutes"],
            error_message=data["error_message"],
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            task_type=MigrationTaskType(data["task_type"]),
            execution_params=(
                tuple(tuple(pair) for pair in data["execution_params"]) if data["execution_params"] else None
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    async def save(self, task: MigrationTask) -> None:
        await self._doc(COLLECTION, task.id).set(self._to_dict(task))

    async def save_batch(self, tasks: list[MigrationTask]) -> None:
        batch = self.client.batch()
        for task in tasks:
            batch.set(self._doc(COLLECTION, task.id), self._to_dict(task))
        await batch.commit()

    async def get_by_id(self, id: str) -> MigrationTask | None:
        doc = await self._doc(COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_dict(doc.to_dict())

    async def list_by_programme(self, programme_id: str) -> list[MigrationTask]:
        query = self._collection(COLLECTION).where("programme_id", "==", programme_id)
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]

    async def get_pending_tasks(self, programme_id: str) -> list[MigrationTask]:
        query = (
            self._collection(COLLECTION)
            .where("programme_id", "==", programme_id)
            .where("status", "==", MigrationTaskStatus.PENDING.value)
        )
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]

    async def update_status(self, task_id: str, status: MigrationTaskStatus) -> None:
        await self._doc(COLLECTION, task_id).update({"status": status.value})
