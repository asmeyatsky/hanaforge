"""InMemoryCutoverExecutionRepository — dev-mode in-memory implementation."""

from __future__ import annotations

from domain.entities.cutover_execution import CutoverExecution
from domain.value_objects.cutover_types import ExecutionStatus


class InMemoryCutoverExecutionRepository:
    """Implements CutoverExecutionRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, CutoverExecution] = {}

    async def save(self, execution: CutoverExecution) -> None:
        self._store[execution.id] = execution

    async def get_by_id(self, id: str) -> CutoverExecution | None:
        return self._store.get(id)

    async def get_active(self, programme_id: str) -> CutoverExecution | None:
        active_statuses = (ExecutionStatus.IN_PROGRESS, ExecutionStatus.PAUSED)
        for ex in self._store.values():
            if ex.programme_id == programme_id and ex.status in active_statuses:
                return ex
        # Fallback: return the most recent execution for the programme
        matches = [
            ex for ex in self._store.values() if ex.programme_id == programme_id
        ]
        if matches:
            return max(matches, key=lambda ex: ex.started_at)
        return None
