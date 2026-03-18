"""Firestore-backed CutoverExecutionRepository — production implementation for M07."""

from __future__ import annotations

from domain.entities.cutover_execution import CutoverExecution
from domain.value_objects.cutover_types import ExecutionStatus
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "cutover_executions"


class FirestoreCutoverExecutionRepository(FirestoreBase):
    """Implements CutoverExecutionRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(ex: CutoverExecution) -> dict:
        d = {}
        for field in ex.__dataclass_fields__:
            val = getattr(ex, field)
            if isinstance(val, tuple):
                val = [
                    {
                        k: (v.value if hasattr(v, "value") else (v.isoformat() if hasattr(v, "isoformat") else v))
                        for k, v in item.__dict__.items()
                    }
                    if hasattr(item, "__dataclass_fields__")
                    else item
                    for item in val
                ]
            elif hasattr(val, "value") and isinstance(val.value, str):
                val = val.value
            elif hasattr(val, "isoformat"):
                val = val.isoformat()
            d[field] = val
        return d

    @staticmethod
    def _from_doc(data: dict) -> CutoverExecution:
        from datetime import datetime

        from domain.value_objects.cutover_types import (
            ExecutionStatus,
            GateDecision,
            TaskProgress,
            TaskProgressStatus,
        )

        for ts_field in ("started_at", "completed_at"):
            if isinstance(data.get(ts_field), str):
                data[ts_field] = datetime.fromisoformat(data[ts_field])

        if isinstance(data.get("status"), str):
            data["status"] = ExecutionStatus(data["status"])

        if isinstance(data.get("task_progress"), list):
            progress = []
            for tp in data["task_progress"]:
                if isinstance(tp, dict):
                    if isinstance(tp.get("status"), str):
                        tp["status"] = TaskProgressStatus(tp["status"])
                    if isinstance(tp.get("started_at"), str):
                        tp["started_at"] = datetime.fromisoformat(tp["started_at"])
                    if isinstance(tp.get("completed_at"), str):
                        tp["completed_at"] = datetime.fromisoformat(tp["completed_at"])
                    progress.append(TaskProgress(**tp))
                else:
                    progress.append(tp)
            data["task_progress"] = tuple(progress)

        if isinstance(data.get("gate_decisions"), list):
            gates = []
            for g in data["gate_decisions"]:
                if isinstance(g, dict):
                    if isinstance(g.get("decided_at"), str):
                        g["decided_at"] = datetime.fromisoformat(g["decided_at"])
                    gates.append(GateDecision(**g))
                else:
                    gates.append(g)
            data["gate_decisions"] = tuple(gates)

        return CutoverExecution(**data)

    async def save(self, execution: CutoverExecution) -> None:
        await self._doc(COLLECTION, execution.id).set(self._to_dict(execution))

    async def get_by_id(self, id: str) -> CutoverExecution | None:
        doc = await self._doc(COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_doc(doc.to_dict())

    async def get_active(self, programme_id: str) -> CutoverExecution | None:
        active_statuses = [ExecutionStatus.IN_PROGRESS.value, ExecutionStatus.PAUSED.value]
        for status_val in active_statuses:
            query = (
                self._collection(COLLECTION)
                .where("programme_id", "==", programme_id)
                .where("status", "==", status_val)
                .limit(1)
            )
            async for doc in query.stream():
                return self._from_doc(doc.to_dict())
        # Fallback: most recent
        query = (
            self._collection(COLLECTION)
            .where("programme_id", "==", programme_id)
            .order_by("started_at", direction="DESCENDING")
            .limit(1)
        )
        async for doc in query.stream():
            return self._from_doc(doc.to_dict())
        return None
