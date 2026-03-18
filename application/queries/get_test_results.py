"""GetTestResultsQuery — retrieves test result summaries for a programme."""

from __future__ import annotations

from application.dtos.test_dto import TestResultsResponse, TestScenarioResponse
from domain.ports.test_ports import TestScenarioRepositoryPort
from domain.value_objects.test_types import ProcessArea, TestStatus


class GetTestResultsQuery:
    """Read-only query: fetch test scenarios and summarise results."""

    def __init__(self, scenario_repo: TestScenarioRepositoryPort) -> None:
        self._scenario_repo = scenario_repo

    async def execute(
        self,
        programme_id: str,
        process_area: ProcessArea | None = None,
    ) -> TestResultsResponse:
        if process_area is not None:
            scenarios = await self._scenario_repo.list_by_process_area(
                programme_id, process_area
            )
        else:
            scenarios = await self._scenario_repo.list_by_programme(programme_id)

        by_status: dict[str, int] = {}
        by_process_area: dict[str, int] = {}

        for s in scenarios:
            status_key = s.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1

            area_key = s.process_area.value
            by_process_area[area_key] = by_process_area.get(area_key, 0) + 1

        # Coverage: percentage of scenarios that have passed
        passed = by_status.get(TestStatus.PASSED.value, 0)
        total = len(scenarios)
        coverage = round((passed / total) * 100.0, 2) if total > 0 else 0.0

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
            for s in scenarios
        ]

        return TestResultsResponse(
            programme_id=programme_id,
            total_scenarios=total,
            by_status=by_status,
            by_process_area=by_process_area,
            coverage_percentage=coverage,
            scenarios=scenario_responses,
        )
