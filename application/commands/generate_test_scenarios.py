"""GenerateTestScenariosUseCase — orchestrates AI-driven test scenario generation."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from application.dtos.test_dto import TestGenerationResponse, TestScenarioResponse
from domain.entities.test_suite import TestSuite
from domain.events.test_events import TestGenerationCompletedEvent
from domain.ports.event_bus_ports import EventBusPort
from domain.ports.test_ports import (
    TestGeneratorPort,
    TestScenarioRepositoryPort,
    TestSuiteRepositoryPort,
)
from domain.value_objects.test_types import ProcessArea


class GenerateTestScenariosUseCase:
    """Generate end-to-end test scenarios for SAP business processes.

    When process_area is None, generates for ALL process areas in PARALLEL
    using asyncio.gather for maximum throughput.
    """

    def __init__(
        self,
        scenario_repo: TestScenarioRepositoryPort,
        suite_repo: TestSuiteRepositoryPort,
        test_generator: TestGeneratorPort,
        event_bus: EventBusPort,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._suite_repo = suite_repo
        self._test_generator = test_generator
        self._event_bus = event_bus

    async def execute(
        self,
        programme_id: str,
        process_area: ProcessArea | None,
        process_definitions: list[dict],
        sap_version: str,
    ) -> TestGenerationResponse:
        # Determine which process areas to generate for
        if process_area is not None:
            areas = [process_area]
        else:
            areas = [
                ProcessArea.ORDER_TO_CASH,
                ProcessArea.PROCURE_TO_PAY,
                ProcessArea.RECORD_TO_REPORT,
                ProcessArea.HIRE_TO_RETIRE,
                ProcessArea.PLAN_TO_PRODUCE,
            ]

        # Generate scenarios for all areas in PARALLEL
        tasks = [
            self._test_generator.generate_test_scenarios(
                process_area=area,
                process_definitions=process_definitions,
                sap_version=sap_version,
            )
            for area in areas
        ]
        results = await asyncio.gather(*tasks)

        # Flatten and tag each scenario with programme_id
        all_scenarios = []
        by_process_area: dict[str, int] = {}
        for area, scenarios in zip(areas, results):
            by_process_area[area.value] = len(scenarios)
            all_scenarios.extend(scenarios)

        # Persist all scenarios in batch
        if all_scenarios:
            await self._scenario_repo.save_batch(all_scenarios)

        # Create a TestSuite per process area
        now = datetime.now(timezone.utc)
        for area, scenarios in zip(areas, results):
            if not scenarios:
                continue
            suite = TestSuite(
                id=str(uuid.uuid4()),
                programme_id=programme_id,
                name=f"{area.value} Test Suite",
                description=f"Auto-generated test suite for {area.value}",
                process_area=area,
                scenarios=tuple(s.id for s in scenarios),
                coverage_percentage=0.0,
                created_at=now,
            )
            await self._suite_repo.save(suite)

        # Publish completion event
        event = TestGenerationCompletedEvent(
            aggregate_id=programme_id,
            scenarios_generated=len(all_scenarios),
            process_areas=tuple(a.value for a in areas),
        )
        await self._event_bus.publish(event)

        # Build response
        scenario_responses = [
            TestScenarioResponse(
                id=s.id,
                scenario_name=s.scenario_name,
                process_area=s.process_area.value,
                description=s.description,
                steps_count=len(s.steps),
                priority=s.priority.value,
                status=s.status.value,
                sap_transaction=s.sap_transaction,
                fiori_app_id=s.fiori_app_id,
                tags=list(s.tags),
            )
            for s in all_scenarios
        ]

        return TestGenerationResponse(
            programme_id=programme_id,
            total_generated=len(all_scenarios),
            by_process_area=by_process_area,
            scenarios=scenario_responses,
        )
