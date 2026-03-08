"""EvaluateGateUseCase — evaluates a go/no-go decision gate during cutover."""

from __future__ import annotations

from dataclasses import replace

from domain.events.cutover_events import GoNoGoGateEvaluatedEvent
from domain.ports.cutover_ports import (
    CutoverExecutionRepositoryPort,
    RunbookRepositoryPort,
)
from domain.ports.event_bus_ports import EventBusPort
from domain.services.gate_evaluation_service import GateEvaluationService

from application.dtos.cutover_dto import GateEvaluationResponse


class EvaluateGateUseCase:
    """Single-responsibility use case: evaluate a specific go/no-go gate."""

    def __init__(
        self,
        runbook_repository: RunbookRepositoryPort,
        execution_repository: CutoverExecutionRepositoryPort,
        event_bus: EventBusPort,
        gate_service: GateEvaluationService | None = None,
    ) -> None:
        self._runbook_repo = runbook_repository
        self._execution_repo = execution_repository
        self._event_bus = event_bus
        self._gate_service = gate_service or GateEvaluationService()

    async def execute(
        self,
        execution_id: str,
        gate_id: str,
        system_checks: dict,
    ) -> GateEvaluationResponse:
        execution = await self._execution_repo.get_by_id(execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        runbook = await self._runbook_repo.get_by_id(execution.runbook_id)
        if runbook is None:
            raise ValueError(f"Runbook {execution.runbook_id} not found")

        # Find the gate
        gate = None
        gate_index = -1
        for idx, g in enumerate(runbook.go_nogo_gates):
            if g.id == gate_id:
                gate = g
                gate_index = idx
                break

        if gate is None:
            raise ValueError(f"Gate {gate_id} not found in runbook")

        # Evaluate the gate
        evaluated_gate = self._gate_service.evaluate_gate(gate, system_checks)

        # Update the runbook with the evaluated gate
        updated_gates = list(runbook.go_nogo_gates)
        updated_gates[gate_index] = evaluated_gate
        updated_runbook = replace(runbook, go_nogo_gates=tuple(updated_gates))
        await self._runbook_repo.save(updated_runbook)

        # Publish event
        event = GoNoGoGateEvaluatedEvent(
            aggregate_id=execution_id,
            programme_id=execution.programme_id,
            gate_name=evaluated_gate.name,
            status=evaluated_gate.status.value,
        )
        await self._event_bus.publish([event])

        checks_data = [
            {
                "name": c.name,
                "check_type": c.check_type,
                "target_value": c.target_value,
                "actual_value": c.actual_value,
                "passed": c.passed,
            }
            for c in evaluated_gate.checks
        ]

        return GateEvaluationResponse(
            gate_id=evaluated_gate.id,
            gate_name=evaluated_gate.name,
            status=evaluated_gate.status.value,
            checks=checks_data,
        )
