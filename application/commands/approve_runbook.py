"""ApproveRunbookUseCase — approves a cutover runbook for execution."""

from __future__ import annotations

from application.dtos.cutover_dto import RunbookResponse
from domain.events.cutover_events import RunbookApprovedEvent
from domain.ports.cutover_ports import RunbookRepositoryPort
from domain.ports.event_bus_ports import EventBusPort


class ApproveRunbookUseCase:
    """Single-responsibility use case: approve a DRAFT runbook."""

    def __init__(
        self,
        runbook_repository: RunbookRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._repository = runbook_repository
        self._event_bus = event_bus

    async def execute(self, runbook_id: str, approver: str) -> RunbookResponse:
        runbook = await self._repository.get_by_id(runbook_id)
        if runbook is None:
            raise ValueError(f"Runbook {runbook_id} not found")

        approved = runbook.approve(approver)
        await self._repository.save(approved)

        event = RunbookApprovedEvent(
            aggregate_id=approved.id,
            programme_id=approved.programme_id,
            runbook_id=approved.id,
            approved_by=approver,
        )
        await self._event_bus.publish([event])

        return RunbookResponse.from_entity(approved)
