"""StartCutoverUseCase — creates a CutoverExecution from an approved runbook."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.entities.cutover_execution import CutoverExecution
from domain.events.cutover_events import CutoverStartedEvent
from domain.ports.cutover_ports import (
    CutoverExecutionRepositoryPort,
    RunbookRepositoryPort,
)
from domain.ports.event_bus_ports import EventBusPort
from domain.value_objects.cutover_types import ExecutionStatus, TaskExecution

from application.dtos.cutover_dto import CutoverExecutionResponse


class StartCutoverUseCase:
    """Single-responsibility use case: initiate cutover execution from an approved runbook."""

    def __init__(
        self,
        runbook_repository: RunbookRepositoryPort,
        execution_repository: CutoverExecutionRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._runbook_repo = runbook_repository
        self._execution_repo = execution_repository
        self._event_bus = event_bus

    async def execute(self, runbook_id: str) -> CutoverExecutionResponse:
        runbook = await self._runbook_repo.get_by_id(runbook_id)
        if runbook is None:
            raise ValueError(f"Runbook {runbook_id} not found")

        # Transition runbook to IN_EXECUTION
        in_exec_runbook = runbook.start_execution()
        await self._runbook_repo.save(in_exec_runbook)

        # Calculate planned duration from tasks
        planned_minutes = sum(t.estimated_duration_minutes for t in runbook.tasks)

        # Build initial task statuses
        task_statuses = tuple(
            TaskExecution(
                task_id=task.id,
                task_name=task.name,
                status="NOT_STARTED",
            )
            for task in runbook.tasks
        )

        now = datetime.now(timezone.utc)
        execution_id = str(uuid.uuid4())

        execution = CutoverExecution(
            id=execution_id,
            runbook_id=runbook.id,
            programme_id=runbook.programme_id,
            started_at=now,
            status=ExecutionStatus.IN_PROGRESS,
            task_statuses=task_statuses,
            planned_duration_minutes=planned_minutes,
        )

        await self._execution_repo.save(execution)

        event = CutoverStartedEvent(
            aggregate_id=execution_id,
            programme_id=runbook.programme_id,
            execution_id=execution_id,
            planned_duration_minutes=planned_minutes,
        )
        await self._event_bus.publish([event])

        return CutoverExecutionResponse.from_entity(execution)
