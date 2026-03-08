"""GetTraceabilityMatrixQuery — builds and returns the traceability matrix for a programme."""

from __future__ import annotations

from domain.ports.test_ports import TestScenarioRepositoryPort, TestSuiteRepositoryPort
from domain.services.test_generation_service import TestGenerationService

from application.dtos.test_dto import TraceabilityMatrixResponse


class GetTraceabilityMatrixQuery:
    """Read-only query: build traceability matrix mapping processes to test scenarios."""

    def __init__(
        self,
        scenario_repo: TestScenarioRepositoryPort,
        suite_repo: TestSuiteRepositoryPort,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._suite_repo = suite_repo
        self._service = TestGenerationService()

    async def execute(self, programme_id: str) -> TraceabilityMatrixResponse:
        scenarios = await self._scenario_repo.list_by_programme(programme_id)
        suites = await self._suite_repo.list_by_programme(programme_id)

        # Build process list from suites (each suite represents a process area)
        processes: list[dict] = []
        for suite in suites:
            processes.append(
                {
                    "id": suite.id,
                    "name": suite.name,
                }
            )

        entries = self._service.build_traceability_matrix(processes, scenarios)

        # Serialize entries
        entry_dicts = [
            {
                "process_id": e.process_id,
                "process_name": e.process_name,
                "test_scenario_id": e.test_scenario_id,
                "test_scenario_name": e.test_scenario_name,
                "defect_ids": list(e.defect_ids),
                "coverage_status": e.coverage_status,
            }
            for e in entries
        ]

        covered = sum(1 for e in entries if e.coverage_status == "COVERED")
        total = len(processes)
        coverage_pct = round((covered / total) * 100.0, 2) if total > 0 else 0.0

        untested = [
            e.process_name for e in entries if e.coverage_status == "NOT_COVERED"
        ]

        return TraceabilityMatrixResponse(
            programme_id=programme_id,
            entries=entry_dicts,
            coverage_percentage=coverage_pct,
            untested_processes=untested,
        )
