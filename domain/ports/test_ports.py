"""Test ports — async boundaries for AI test generation, export, and persistence."""

from __future__ import annotations

from typing import Protocol

from domain.entities.test_scenario import TestScenario
from domain.entities.test_suite import TestSuite
from domain.value_objects.test_types import (
    ProcessArea,
    TestExportFormat,
    TestStatus,
)


class TestGeneratorPort(Protocol):
    """AI-powered test scenario generation."""

    async def generate_test_scenarios(
        self,
        process_area: ProcessArea,
        process_definitions: list[dict],
        sap_version: str,
    ) -> list[TestScenario]: ...


class TestExporterPort(Protocol):
    """Export test scenarios to various test management tool formats."""

    async def export_scenarios(
        self,
        scenarios: list[TestScenario],
        format: TestExportFormat,
    ) -> bytes: ...


class TestScenarioRepositoryPort(Protocol):
    """Persistence boundary for TestScenario aggregates."""

    async def save(self, scenario: TestScenario) -> None: ...
    async def save_batch(self, scenarios: list[TestScenario]) -> None: ...
    async def get_by_id(self, id: str) -> TestScenario | None: ...
    async def list_by_programme(self, programme_id: str) -> list[TestScenario]: ...
    async def list_by_process_area(
        self, programme_id: str, process_area: ProcessArea
    ) -> list[TestScenario]: ...
    async def count_by_status(
        self, programme_id: str, status: TestStatus
    ) -> int: ...


class TestSuiteRepositoryPort(Protocol):
    """Persistence boundary for TestSuite aggregates."""

    async def save(self, suite: TestSuite) -> None: ...
    async def get_by_id(self, id: str) -> TestSuite | None: ...
    async def list_by_programme(self, programme_id: str) -> list[TestSuite]: ...
