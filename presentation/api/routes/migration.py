"""Migration routes — orchestration endpoints for migration planning and execution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from application.commands.create_migration_plan import CreateMigrationPlanUseCase
from application.commands.execute_migration_step import ExecuteMigrationStepUseCase
from application.commands.run_migration_batch import RunMigrationBatchUseCase
from application.dtos.migration_dto import (
    AnomalyAlertResponse,
    AuditLogResponse,
    CreateMigrationPlanRequest,
    MigrationBatchResponse,
    MigrationPlanResponse,
    MigrationStatusResponse,
    MigrationTaskResponse,
)
from application.queries.get_audit_log import GetAuditLogQuery
from application.queries.get_migration_status import GetMigrationStatusQuery
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["Migration Orchestrator"])


@router.post(
    "/plan/{programme_id}",
    response_model=MigrationPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a migration plan",
)
async def create_migration_plan(
    programme_id: str,
    body: CreateMigrationPlanRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> MigrationPlanResponse:
    """Generate a full migration task graph for a programme based on the chosen approach."""
    container = request.app.state.container
    use_case: CreateMigrationPlanUseCase = container.resolve(CreateMigrationPlanUseCase)
    return await use_case.execute(programme_id=programme_id, request=body)


@router.get(
    "/status/{programme_id}",
    response_model=MigrationStatusResponse,
    summary="Get migration status",
)
async def get_migration_status(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> MigrationStatusResponse:
    """Retrieve full migration status including health, critical path, and task summary."""
    container = request.app.state.container
    query: GetMigrationStatusQuery = container.resolve(GetMigrationStatusQuery)
    return await query.execute(programme_id=programme_id)


@router.post(
    "/execute/{task_id}",
    response_model=MigrationTaskResponse,
    summary="Execute a single migration task",
)
async def execute_migration_step(
    task_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> MigrationTaskResponse:
    """Execute a single migration task after validating its dependencies are complete."""
    container = request.app.state.container
    use_case: ExecuteMigrationStepUseCase = container.resolve(ExecuteMigrationStepUseCase)
    try:
        return await use_case.execute(task_id=task_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/batch/{programme_id}",
    response_model=MigrationBatchResponse,
    summary="Run batch of ready migration tasks",
)
async def run_migration_batch(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> MigrationBatchResponse:
    """Execute all ready migration tasks in parallel batches."""
    container = request.app.state.container
    use_case: RunMigrationBatchUseCase = container.resolve(RunMigrationBatchUseCase)
    return await use_case.execute(programme_id=programme_id)


@router.get(
    "/audit/{programme_id}",
    response_model=AuditLogResponse,
    summary="Get migration audit log",
)
async def get_audit_log(
    programme_id: str,
    request: Request,
    limit: int = 100,
    _user=Depends(get_current_user),
) -> AuditLogResponse:
    """Retrieve the migration audit log for compliance and traceability."""
    container = request.app.state.container
    query: GetAuditLogQuery = container.resolve(GetAuditLogQuery)
    return await query.execute(programme_id=programme_id, limit=limit)


@router.get(
    "/anomalies/{programme_id}",
    response_model=list[AnomalyAlertResponse],
    summary="Get active anomalies",
)
async def get_active_anomalies(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> list[AnomalyAlertResponse]:
    """Retrieve active (unacknowledged) anomaly alerts for a programme."""
    container = request.app.state.container
    anomaly_repo = container.resolve("AnomalyRepositoryPort")
    anomalies = await anomaly_repo.list_active(programme_id)
    return [AnomalyAlertResponse.from_value_object(a) for a in anomalies]


@router.post(
    "/anomalies/{alert_id}/acknowledge",
    status_code=status.HTTP_200_OK,
    summary="Acknowledge an anomaly alert",
)
async def acknowledge_anomaly(
    alert_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> dict:
    """Mark an anomaly alert as acknowledged/reviewed."""
    container = request.app.state.container
    anomaly_repo = container.resolve("AnomalyRepositoryPort")
    await anomaly_repo.acknowledge(alert_id)
    return {"status": "acknowledged", "alert_id": alert_id}
