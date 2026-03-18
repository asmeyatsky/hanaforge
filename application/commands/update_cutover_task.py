"""UpdateCutoverTaskUseCase — updates the status of a task during cutover execution."""

from __future__ import annotations

from application.dtos.cutover_dto import CutoverExecutionResponse
from domain.ports.cutover_ports import CutoverExecutionRepositoryPort
from domain.ports.event_bus_ports import EventBusPort


class UpdateCutoverTaskUseCase:
    """Single-responsibility use case: update a task's status within a running execution."""

    def __init__(
        self,
        execution_repository: CutoverExecutionRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._execution_repo = execution_repository
        self._event_bus = event_bus

    async def execute(
        self,
        execution_id: str,
        task_id: str,
        status: str,
        notes: str | None = None,
        executor: str | None = None,
    ) -> CutoverExecutionResponse:
        execution = await self._execution_repo.get_by_id(execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        updated = execution.update_task(
            task_id=task_id,
            status=status,
            notes=notes,
            executor=executor,
        )

        await self._execution_repo.save(updated)

        return CutoverExecutionResponse.from_entity(updated)
