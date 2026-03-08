"""InMemoryTestSuiteRepository — dev-mode in-memory implementation of TestSuiteRepositoryPort."""

from __future__ import annotations

from domain.entities.test_suite import TestSuite


class InMemoryTestSuiteRepository:
    """Implements TestSuiteRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, TestSuite] = {}

    async def save(self, suite: TestSuite) -> None:
        self._store[suite.id] = suite

    async def get_by_id(self, id: str) -> TestSuite | None:
        return self._store.get(id)

    async def list_by_programme(self, programme_id: str) -> list[TestSuite]:
        return [
            s for s in self._store.values()
            if s.programme_id == programme_id
        ]
