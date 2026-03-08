"""GenerateRunbookUseCase — generates a structured cutover runbook from programme artefacts."""

from __future__ import annotations

from domain.events.cutover_events import RunbookGeneratedEvent
from domain.ports.cutover_ports import RunbookRepositoryPort
from domain.ports.event_bus_ports import EventBusPort
from domain.services.runbook_generation_service import RunbookGenerationService

from application.dtos.cutover_dto import RunbookResponse


class GenerateRunbookUseCase:
    """Single-responsibility use case: generate and persist a cutover runbook."""

    def __init__(
        self,
        runbook_repository: RunbookRepositoryPort,
        event_bus: EventBusPort,
        generation_service: RunbookGenerationService | None = None,
    ) -> None:
        self._repository = runbook_repository
        self._event_bus = event_bus
        self._generation_service = generation_service or RunbookGenerationService()

    async def execute(
        self,
        programme_id: str,
        migration_tasks: list[dict],
        integration_inventory: list[dict],
        data_sequences: list[dict],
    ) -> RunbookResponse:
        runbook = self._generation_service.generate_runbook(
            programme_id=programme_id,
            migration_tasks=migration_tasks,
            integration_inventory=integration_inventory,
            data_sequences=data_sequences,
        )

        await self._repository.save(runbook)

        event = RunbookGeneratedEvent(
            aggregate_id=runbook.id,
            programme_id=programme_id,
            runbook_id=runbook.id,
            task_count=len(runbook.tasks),
        )
        await self._event_bus.publish([event])

        return RunbookResponse.from_entity(runbook)
