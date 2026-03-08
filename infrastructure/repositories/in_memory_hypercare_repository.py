"""InMemoryHypercareRepository — dev-mode in-memory implementation."""

from __future__ import annotations

from domain.entities.hypercare_session import HypercareSession
from domain.value_objects.cutover_types import HypercareStatus


class InMemoryHypercareRepository:
    """Implements HypercareRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, HypercareSession] = {}

    async def save(self, session: HypercareSession) -> None:
        self._store[session.id] = session

    async def get_by_id(self, id: str) -> HypercareSession | None:
        return self._store.get(id)

    async def get_active(self, programme_id: str) -> HypercareSession | None:
        active_statuses = (
            HypercareStatus.ACTIVE,
            HypercareStatus.MONITORING,
            HypercareStatus.ESCALATED,
        )
        for s in self._store.values():
            if s.programme_id == programme_id and s.status in active_statuses:
                return s
        return None
