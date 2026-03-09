"""Cutover Commander routes — API endpoints for cutover lifecycle management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from application.commands.approve_runbook import ApproveRunbookUseCase
from application.commands.evaluate_gate import EvaluateGateUseCase
from application.commands.generate_lessons_learned import GenerateLessonsLearnedUseCase
from application.commands.generate_runbook import GenerateRunbookUseCase
from application.commands.log_hypercare_incident import LogHypercareIncidentUseCase
from application.commands.start_cutover import StartCutoverUseCase
from application.commands.start_hypercare import StartHypercareUseCase
from application.commands.update_cutover_task import UpdateCutoverTaskUseCase
from application.dtos.cutover_dto import (
    CutoverExecutionResponse,
    CutoverStatusResponse,
    GateEvaluationResponse,
    GenerateRunbookRequest,
    HypercareResponse,
    LessonsLearnedResponse,
    RunbookResponse,
    StartHypercareRequest,
)
from application.queries.get_cutover_status import GetCutoverStatusQuery
from application.queries.get_hypercare_status import GetHypercareStatusQuery
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["Cutover Commander"])


# ---------------------------------------------------------------------------
# Runbook endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/runbook/{programme_id}",
    response_model=RunbookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a cutover runbook",
)
async def generate_runbook(
    programme_id: str,
    body: GenerateRunbookRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> RunbookResponse:
    """Generate a structured SAP cutover runbook from programme artefacts."""
    container = request.app.state.container
    use_case: GenerateRunbookUseCase = container.resolve(GenerateRunbookUseCase)
    return await use_case.execute(
        programme_id=programme_id,
        migration_tasks=body.migration_tasks,
        integration_inventory=body.integration_inventory,
        data_sequences=body.data_sequences,
    )


@router.post(
    "/runbook/{runbook_id}/approve",
    response_model=RunbookResponse,
    summary="Approve a cutover runbook",
)
async def approve_runbook(
    runbook_id: str,
    request: Request,
    approver: str = "system",
    _user=Depends(get_current_user),
) -> RunbookResponse:
    """Approve a DRAFT cutover runbook for execution."""
    container = request.app.state.container
    use_case: ApproveRunbookUseCase = container.resolve(ApproveRunbookUseCase)
    try:
        return await use_case.execute(runbook_id=runbook_id, approver=approver)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


# ---------------------------------------------------------------------------
# Execution endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/execute/{runbook_id}",
    response_model=CutoverExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start cutover execution",
)
async def start_cutover(
    runbook_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> CutoverExecutionResponse:
    """Start cutover execution from an approved runbook."""
    container = request.app.state.container
    use_case: StartCutoverUseCase = container.resolve(StartCutoverUseCase)
    try:
        return await use_case.execute(runbook_id=runbook_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get(
    "/status/{programme_id}",
    response_model=CutoverStatusResponse,
    summary="Get cutover status",
)
async def get_cutover_status(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> CutoverStatusResponse:
    """Get comprehensive cutover status including runbook, execution, and gates."""
    container = request.app.state.container
    query: GetCutoverStatusQuery = container.resolve(GetCutoverStatusQuery)
    return await query.execute(programme_id=programme_id)


# ---------------------------------------------------------------------------
# Gate evaluation
# ---------------------------------------------------------------------------


@router.post(
    "/gate/{execution_id}/{gate_id}",
    response_model=GateEvaluationResponse,
    summary="Evaluate a go/no-go gate",
)
async def evaluate_gate(
    execution_id: str,
    gate_id: str,
    body: dict,
    request: Request,
    _user=Depends(get_current_user),
) -> GateEvaluationResponse:
    """Evaluate a go/no-go decision gate with system health check results."""
    container = request.app.state.container
    use_case: EvaluateGateUseCase = container.resolve(EvaluateGateUseCase)
    try:
        return await use_case.execute(
            execution_id=execution_id,
            gate_id=gate_id,
            system_checks=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


# ---------------------------------------------------------------------------
# Task updates
# ---------------------------------------------------------------------------


@router.put(
    "/task/{execution_id}/{task_id}",
    response_model=CutoverExecutionResponse,
    summary="Update a cutover task status",
)
async def update_task(
    execution_id: str,
    task_id: str,
    body: dict,
    request: Request,
    _user=Depends(get_current_user),
) -> CutoverExecutionResponse:
    """Update the status of a task during cutover execution."""
    container = request.app.state.container
    use_case: UpdateCutoverTaskUseCase = container.resolve(UpdateCutoverTaskUseCase)
    try:
        return await use_case.execute(
            execution_id=execution_id,
            task_id=task_id,
            status=body.get("status", "IN_PROGRESS"),
            notes=body.get("notes"),
            executor=body.get("executor"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


# ---------------------------------------------------------------------------
# Hypercare endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/hypercare/{programme_id}",
    response_model=HypercareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start hypercare session",
)
async def start_hypercare(
    programme_id: str,
    body: StartHypercareRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> HypercareResponse:
    """Start a hypercare monitoring session for a programme."""
    container = request.app.state.container
    use_case: StartHypercareUseCase = container.resolve(StartHypercareUseCase)
    return await use_case.execute(
        programme_id=programme_id,
        duration_days=body.duration_days,
        monitoring_config=body.monitoring_config,
    )


@router.post(
    "/hypercare/{session_id}/incident",
    response_model=HypercareResponse,
    summary="Log hypercare incident",
)
async def log_incident(
    session_id: str,
    body: dict,
    request: Request,
    _user=Depends(get_current_user),
) -> HypercareResponse:
    """Log an incident during the hypercare period."""
    container = request.app.state.container
    use_case: LogHypercareIncidentUseCase = container.resolve(
        LogHypercareIncidentUseCase
    )
    try:
        return await use_case.execute(
            session_id=session_id,
            severity=body.get("severity", "MEDIUM"),
            description=body.get("description", ""),
            sap_component=body.get("sap_component"),
            ticket_id=body.get("ticket_id"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get(
    "/hypercare/{programme_id}",
    response_model=HypercareResponse,
    summary="Get hypercare status",
)
async def get_hypercare_status(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> HypercareResponse:
    """Get active hypercare session status for a programme."""
    container = request.app.state.container
    query: GetHypercareStatusQuery = container.resolve(GetHypercareStatusQuery)
    result = await query.execute(programme_id=programme_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active hypercare session for programme {programme_id!r}",
        )
    return result


# ---------------------------------------------------------------------------
# Lessons Learned
# ---------------------------------------------------------------------------


@router.post(
    "/lessons-learned/{programme_id}",
    response_model=LessonsLearnedResponse,
    summary="Generate lessons learned",
)
async def generate_lessons_learned(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> LessonsLearnedResponse:
    """Analyse cutover execution and hypercare to generate lessons-learned document."""
    container = request.app.state.container
    use_case: GenerateLessonsLearnedUseCase = container.resolve(
        GenerateLessonsLearnedUseCase
    )
    try:
        return await use_case.execute(programme_id=programme_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
