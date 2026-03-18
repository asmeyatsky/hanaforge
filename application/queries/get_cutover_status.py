"""GetCutoverStatusQuery — retrieves comprehensive cutover status for a programme."""

from __future__ import annotations

from application.dtos.cutover_dto import (
    CutoverExecutionResponse,
    CutoverStatusResponse,
    GoNoGoGateResponse,
    RunbookResponse,
)
from domain.ports.cutover_ports import (
    CutoverExecutionRepositoryPort,
    RunbookRepositoryPort,
)


class GetCutoverStatusQuery:
    """Read-only query: fetch cutover status including runbook, execution, and gates."""

    def __init__(
        self,
        runbook_repository: RunbookRepositoryPort,
        execution_repository: CutoverExecutionRepositoryPort,
    ) -> None:
        self._runbook_repo = runbook_repository
        self._execution_repo = execution_repository

    async def execute(self, programme_id: str) -> CutoverStatusResponse:
        runbook = await self._runbook_repo.get_latest_by_programme(programme_id)
        execution = await self._execution_repo.get_active(programme_id)

        runbook_resp = RunbookResponse.from_entity(runbook) if runbook else None
        execution_resp = (
            CutoverExecutionResponse.from_entity(execution) if execution else None
        )

        gates: list[GoNoGoGateResponse] = []
        if runbook:
            for gate in runbook.go_nogo_gates:
                checks_data = [
                    {
                        "name": c.name,
                        "check_type": c.check_type,
                        "target_value": c.target_value,
                        "actual_value": c.actual_value,
                        "passed": c.passed,
                    }
                    for c in gate.checks
                ]
                gates.append(
                    GoNoGoGateResponse(
                        id=gate.id,
                        name=gate.name,
                        gate_type=gate.gate_type.value,
                        status=gate.status.value,
                        checks=checks_data,
                    )
                )

        # Calculate critical path deviation
        deviation = 0
        if execution:
            deviation = execution.elapsed_minutes - execution.planned_duration_minutes

        return CutoverStatusResponse(
            programme_id=programme_id,
            runbook=runbook_resp,
            execution=execution_resp,
            gates=gates,
            critical_path_deviation_minutes=max(0, deviation),
        )
