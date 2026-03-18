"""ExportTestScenariosUseCase — exports test scenarios to various test management formats."""

from __future__ import annotations

from domain.ports.test_ports import TestExporterPort, TestScenarioRepositoryPort
from domain.value_objects.test_types import ProcessArea, TestExportFormat


class ExportTestScenariosUseCase:
    """Fetch scenarios and export them via the configured exporter port."""

    def __init__(
        self,
        scenario_repo: TestScenarioRepositoryPort,
        exporter: TestExporterPort,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._exporter = exporter

    async def execute(
        self,
        programme_id: str,
        format: TestExportFormat,
        process_area: ProcessArea | None = None,
    ) -> bytes:
        if process_area is not None:
            scenarios = await self._scenario_repo.list_by_process_area(programme_id, process_area)
        else:
            scenarios = await self._scenario_repo.list_by_programme(programme_id)

        return await self._exporter.export_scenarios(scenarios, format)
