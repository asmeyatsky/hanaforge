"""InMemoryTestScenarioRepository — dev-mode in-memory implementation of TestScenarioRepositoryPort."""

from __future__ import annotations

from domain.entities.test_scenario import TestScenario
from domain.value_objects.test_types import ProcessArea, TestStatus


class InMemoryTestScenarioRepository:
    """Implements TestScenarioRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, TestScenario] = {}

    async def save(self, scenario: TestScenario) -> None:
        self._store[scenario.id] = scenario

    async def save_batch(self, scenarios: list[TestScenario]) -> None:
        for scenario in scenarios:
            self._store[scenario.id] = scenario

    async def get_by_id(self, id: str) -> TestScenario | None:
        return self._store.get(id)

    async def list_by_programme(self, programme_id: str) -> list[TestScenario]:
        return [s for s in self._store.values() if s.programme_id == programme_id]

    async def list_by_process_area(self, programme_id: str, process_area: ProcessArea) -> list[TestScenario]:
        return [s for s in self._store.values() if s.programme_id == programme_id and s.process_area == process_area]

    async def count_by_status(self, programme_id: str, status: TestStatus) -> int:
        return sum(1 for s in self._store.values() if s.programme_id == programme_id and s.status == status)
