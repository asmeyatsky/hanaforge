"""GenerateInterfaceTestsUseCase — generates test cases for IDoc/RFC/BAPI interfaces."""

from __future__ import annotations

import asyncio

from application.dtos.test_dto import TestGenerationResponse, TestScenarioResponse
from domain.ports.event_bus_ports import EventBusPort
from domain.ports.test_ports import TestScenarioRepositoryPort
from domain.services.test_generation_service import TestGenerationService
from domain.value_objects.test_types import InterfaceTestType


class GenerateInterfaceTestsUseCase:
    """Generate test scenarios for each IDoc/RFC/BAPI interface in PARALLEL."""

    def __init__(
        self,
        scenario_repo: TestScenarioRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._event_bus = event_bus
        self._service = TestGenerationService()

    async def execute(
        self,
        programme_id: str,
        interfaces: list[dict],
    ) -> TestGenerationResponse:
        # Generate interface test scenarios in parallel
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                None,
                self._generate_single,
                programme_id,
                iface,
            )
            for iface in interfaces
        ]
        scenarios = await asyncio.gather(*tasks)

        # Persist all generated scenarios in batch
        scenario_list = list(scenarios)
        if scenario_list:
            await self._scenario_repo.save_batch(scenario_list)

        by_process_area: dict[str, int] = {}
        for s in scenario_list:
            area = s.process_area.value
            by_process_area[area] = by_process_area.get(area, 0) + 1

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
            for s in scenario_list
        ]

        return TestGenerationResponse(
            programme_id=programme_id,
            total_generated=len(scenario_list),
            by_process_area=by_process_area,
            scenarios=scenario_responses,
        )

    def _generate_single(self, programme_id: str, iface: dict):
        """Synchronous helper for thread-pool execution."""
        interface_type = InterfaceTestType(iface.get("type", "RFC"))
        interface_name = iface.get("name", "Unknown")
        config = {**iface, "programme_id": programme_id}
        return self._service.generate_interface_test(
            interface_type=interface_type,
            interface_name=interface_name,
            interface_config=config,
        )
