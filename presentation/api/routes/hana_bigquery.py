"""HANA → BigQuery data pipeline API."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from application.commands.create_data_pipeline import CreateDataPipelineUseCase
from application.commands.start_pipeline_run import StartPipelineRunUseCase
from application.commands.validate_data_pipeline import ValidateDataPipelineUseCase
from application.dtos.hana_bq_dto import (
    CreateDataPipelineRequest,
    DataPipelineListResponse,
    DataPipelineResponse,
    HanaConnectionParams,
    PipelineRunListResponse,
    PipelineRunResponse,
    StartPipelineRunBody,
    StartPipelineRunRequest,
    ValidatePipelineResponse,
)
from application.queries.get_data_pipeline import GetDataPipelineQuery
from application.queries.get_pipeline_run import GetPipelineRunQuery
from application.queries.list_data_pipelines import ListDataPipelinesQuery
from application.queries.list_pipeline_runs import ListPipelineRunsQuery
from application.services.hana_connection_merge import merge_hana_connection_params
from domain.services.tenant_access_service import TenantAccessService
from infrastructure.config.dependency_injection import Container
from presentation.api.middleware.auth import get_current_user
from presentation.api.middleware.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="", tags=["HANA → BigQuery"])


async def _require_programme(
    programme_id: str,
    tenant: TenantContext,
    container: Container,
) -> None:
    tenant_svc: TenantAccessService = container.resolve(TenantAccessService)
    try:
        await tenant_svc.validate_programme_access(
            programme_id=programme_id,
            customer_id=tenant.customer_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programme {programme_id!r} not found",
        )


@router.post(
    "/{programme_id}/hana-bigquery/pipelines",
    response_model=DataPipelineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a HANA → BigQuery pipeline",
)
async def create_hana_bigquery_pipeline(
    programme_id: str,
    body: CreateDataPipelineRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    _user=Depends(get_current_user),
) -> DataPipelineResponse:
    container: Container = request.app.state.container
    await _require_programme(programme_id, tenant, container)
    use_case: CreateDataPipelineUseCase = container.resolve(CreateDataPipelineUseCase)
    try:
        return await use_case.execute(programme_id=programme_id, request=body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/{programme_id}/hana-bigquery/pipelines",
    response_model=DataPipelineListResponse,
    summary="List HANA → BigQuery pipelines",
)
async def list_hana_bigquery_pipelines(
    programme_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    _user=Depends(get_current_user),
) -> DataPipelineListResponse:
    container: Container = request.app.state.container
    await _require_programme(programme_id, tenant, container)
    query: ListDataPipelinesQuery = container.resolve(ListDataPipelinesQuery)
    return await query.execute(programme_id=programme_id)


@router.get(
    "/{programme_id}/hana-bigquery/pipelines/{pipeline_id}",
    response_model=DataPipelineResponse,
    summary="Get a HANA → BigQuery pipeline",
)
async def get_hana_bigquery_pipeline(
    programme_id: str,
    pipeline_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    _user=Depends(get_current_user),
) -> DataPipelineResponse:
    container: Container = request.app.state.container
    await _require_programme(programme_id, tenant, container)
    query: GetDataPipelineQuery = container.resolve(GetDataPipelineQuery)
    result = await query.execute(programme_id=programme_id, pipeline_id=pipeline_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")
    return result


@router.post(
    "/{programme_id}/hana-bigquery/pipelines/{pipeline_id}/validate",
    response_model=ValidatePipelineResponse,
    summary="Validate SAP HANA connectivity for a pipeline",
)
async def validate_hana_bigquery_pipeline(
    programme_id: str,
    pipeline_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    _user=Depends(get_current_user),
    body: HanaConnectionParams | None = Body(None),
) -> ValidatePipelineResponse:
    container: Container = request.app.state.container
    settings = container.settings
    await _require_programme(programme_id, tenant, container)
    use_case: ValidateDataPipelineUseCase = container.resolve(ValidateDataPipelineUseCase)
    params = merge_hana_connection_params(settings, body)
    try:
        return await use_case.execute(programme_id, pipeline_id, params)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/{programme_id}/hana-bigquery/pipelines/{pipeline_id}/runs",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run a HANA → BigQuery pipeline (extract, stage, load)",
)
async def start_hana_bigquery_run(
    programme_id: str,
    pipeline_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    _user=Depends(get_current_user),
    body: StartPipelineRunBody | None = Body(None),
) -> PipelineRunResponse:
    container: Container = request.app.state.container
    settings = container.settings
    await _require_programme(programme_id, tenant, container)
    use_case: StartPipelineRunUseCase = container.resolve(StartPipelineRunUseCase)
    run_body = body or StartPipelineRunBody()
    params = merge_hana_connection_params(settings, run_body.hana_connection)
    req = StartPipelineRunRequest(row_limit_per_table=run_body.row_limit_per_table)
    try:
        return await use_case.execute(
            programme_id=programme_id,
            pipeline_id=pipeline_id,
            connection_params=params,
            request=req,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/{programme_id}/hana-bigquery/pipelines/{pipeline_id}/runs",
    response_model=PipelineRunListResponse,
    summary="List runs for a pipeline",
)
async def list_hana_bigquery_runs(
    programme_id: str,
    pipeline_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    _user=Depends(get_current_user),
) -> PipelineRunListResponse:
    container: Container = request.app.state.container
    await _require_programme(programme_id, tenant, container)
    query: ListPipelineRunsQuery = container.resolve(ListPipelineRunsQuery)
    runs = await query.execute(programme_id=programme_id, pipeline_id=pipeline_id)
    if runs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")
    return PipelineRunListResponse(runs=runs)


@router.get(
    "/{programme_id}/hana-bigquery/pipelines/{pipeline_id}/runs/{run_id}",
    response_model=PipelineRunResponse,
    summary="Get a single pipeline run",
)
async def get_hana_bigquery_run(
    programme_id: str,
    pipeline_id: str,
    run_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    _user=Depends(get_current_user),
) -> PipelineRunResponse:
    container: Container = request.app.state.container
    await _require_programme(programme_id, tenant, container)
    query: GetPipelineRunQuery = container.resolve(GetPipelineRunQuery)
    result = await query.execute(programme_id, pipeline_id, run_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return result
