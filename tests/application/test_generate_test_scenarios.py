"""Tests for GenerateTestScenariosUseCase — mocked ports only."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from application.commands.generate_test_scenarios import GenerateTestScenariosUseCase
from domain.entities.test_scenario import TestScenario
from domain.events.test_events import TestGenerationCompletedEvent
from domain.value_objects.test_types import (
    ProcessArea,
    TestPriority,
    TestStatus,
    TestStep,
)


def _make_scenario(
    process_area: ProcessArea,
    name: str = "Test Scenario",
) -> TestScenario:
    return TestScenario(
        id=str(uuid.uuid4()),
        programme_id="prog-001",
        process_area=process_area,
        scenario_name=name,
        description=f"Auto-generated test for {process_area.value}",
        preconditions=("System is available",),
        steps=(
            TestStep(
                step_number=1,
                action="Execute transaction",
                expected_result="Transaction completes",
            ),
        ),
        expected_outcome="Process completes successfully",
        sap_transaction="VA01",
        fiori_app_id=None,
        priority=TestPriority.MEDIUM,
        status=TestStatus.DRAFT,
        tags=(process_area.value,),
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def mock_scenario_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_suite_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_event_bus() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_test_generator() -> AsyncMock:
    """Mock TestGeneratorPort that returns 2 scenarios per process area."""
    generator = AsyncMock()

    async def generate_side_effect(
        process_area: ProcessArea,
        process_definitions: list[dict],
        sap_version: str,
    ) -> list[TestScenario]:
        return [
            _make_scenario(process_area, f"Scenario 1 for {process_area.value}"),
            _make_scenario(process_area, f"Scenario 2 for {process_area.value}"),
        ]

    generator.generate_test_scenarios.side_effect = generate_side_effect
    return generator


@pytest.fixture()
def use_case(
    mock_scenario_repo: AsyncMock,
    mock_suite_repo: AsyncMock,
    mock_test_generator: AsyncMock,
    mock_event_bus: AsyncMock,
) -> GenerateTestScenariosUseCase:
    return GenerateTestScenariosUseCase(
        scenario_repo=mock_scenario_repo,
        suite_repo=mock_suite_repo,
        test_generator=mock_test_generator,
        event_bus=mock_event_bus,
    )


class TestGenerateTestScenarios:
    @pytest.mark.asyncio
    async def test_generates_for_all_process_areas_in_parallel(
        self,
        use_case: GenerateTestScenariosUseCase,
        mock_test_generator: AsyncMock,
    ) -> None:
        """When process_area is None, all 5 core process areas are generated."""
        result = await use_case.execute(
            programme_id="prog-001",
            process_area=None,
            process_definitions=[{"name": "Test Process"}],
            sap_version="S/4HANA 2023",
        )

        # Should have called the generator for all 5 areas
        assert mock_test_generator.generate_test_scenarios.await_count == 5

        called_areas = {c.kwargs["process_area"] for c in mock_test_generator.generate_test_scenarios.call_args_list}
        assert called_areas == {
            ProcessArea.ORDER_TO_CASH,
            ProcessArea.PROCURE_TO_PAY,
            ProcessArea.RECORD_TO_REPORT,
            ProcessArea.HIRE_TO_RETIRE,
            ProcessArea.PLAN_TO_PRODUCE,
        }

        # 2 scenarios per area * 5 areas = 10 total
        assert result.total_generated == 10

    @pytest.mark.asyncio
    async def test_creates_test_suite_per_area(
        self,
        use_case: GenerateTestScenariosUseCase,
        mock_suite_repo: AsyncMock,
    ) -> None:
        """A TestSuite is created and persisted for each process area."""
        await use_case.execute(
            programme_id="prog-001",
            process_area=None,
            process_definitions=[{"name": "Test Process"}],
            sap_version="S/4HANA 2023",
        )

        # One suite per process area
        assert mock_suite_repo.save.await_count == 5

        saved_suites = [c.args[0] for c in mock_suite_repo.save.call_args_list]
        saved_areas = {s.process_area for s in saved_suites}
        assert saved_areas == {
            ProcessArea.ORDER_TO_CASH,
            ProcessArea.PROCURE_TO_PAY,
            ProcessArea.RECORD_TO_REPORT,
            ProcessArea.HIRE_TO_RETIRE,
            ProcessArea.PLAN_TO_PRODUCE,
        }

        # Each suite should contain 2 scenario IDs
        for suite in saved_suites:
            assert len(suite.scenarios) == 2

    @pytest.mark.asyncio
    async def test_publishes_generation_completed_event(
        self,
        use_case: GenerateTestScenariosUseCase,
        mock_event_bus: AsyncMock,
    ) -> None:
        """A TestGenerationCompletedEvent is published after generation."""
        await use_case.execute(
            programme_id="prog-001",
            process_area=None,
            process_definitions=[{"name": "Test Process"}],
            sap_version="S/4HANA 2023",
        )

        mock_event_bus.publish.assert_awaited_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, TestGenerationCompletedEvent)
        assert published_event.aggregate_id == "prog-001"
        assert published_event.scenarios_generated == 10
        assert len(published_event.process_areas) == 5

    @pytest.mark.asyncio
    async def test_returns_correct_counts(
        self,
        use_case: GenerateTestScenariosUseCase,
    ) -> None:
        """The response contains accurate per-area and total counts."""
        result = await use_case.execute(
            programme_id="prog-001",
            process_area=None,
            process_definitions=[{"name": "Test Process"}],
            sap_version="S/4HANA 2023",
        )

        assert result.programme_id == "prog-001"
        assert result.total_generated == 10
        assert len(result.by_process_area) == 5

        for area in [
            "ORDER_TO_CASH",
            "PROCURE_TO_PAY",
            "RECORD_TO_REPORT",
            "HIRE_TO_RETIRE",
            "PLAN_TO_PRODUCE",
        ]:
            assert result.by_process_area[area] == 2

        assert len(result.scenarios) == 10

    @pytest.mark.asyncio
    async def test_single_process_area(
        self,
        use_case: GenerateTestScenariosUseCase,
        mock_test_generator: AsyncMock,
    ) -> None:
        """When a specific process_area is given, only that area is generated."""
        result = await use_case.execute(
            programme_id="prog-001",
            process_area=ProcessArea.ORDER_TO_CASH,
            process_definitions=[{"name": "Test Process"}],
            sap_version="S/4HANA 2023",
        )

        assert mock_test_generator.generate_test_scenarios.await_count == 1
        assert result.total_generated == 2
        assert result.by_process_area == {"ORDER_TO_CASH": 2}
