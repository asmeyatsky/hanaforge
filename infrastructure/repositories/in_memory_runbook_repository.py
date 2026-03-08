"""InMemoryRunbookRepository — dev-mode in-memory implementation of RunbookRepositoryPort."""

from __future__ import annotations

from domain.entities.cutover_runbook import CutoverRunbook


class InMemoryRunbookRepository:
    """Implements RunbookRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, CutoverRunbook] = {}

    async def save(self, runbook: CutoverRunbook) -> None:
        self._store[runbook.id] = runbook

    async def get_by_id(self, id: str) -> CutoverRunbook | None:
        return self._store.get(id)

    async def get_latest_by_programme(self, programme_id: str) -> CutoverRunbook | None:
        matches = [
            rb for rb in self._store.values() if rb.programme_id == programme_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda rb: rb.version)

    async def list_by_programme(self, programme_id: str) -> list[CutoverRunbook]:
        return [
            rb for rb in self._store.values() if rb.programme_id == programme_id
        ]
