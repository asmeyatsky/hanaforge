"""Programme routes — CRUD endpoints for migration programmes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from application.commands.create_programme import CreateProgrammeUseCase
from application.dtos.programme_dto import (
    CreateProgrammeRequest,
    ProgrammeListResponse,
    ProgrammeResponse,
)
from application.queries.list_programmes import ListProgrammesQuery
from domain.services.tenant_access_service import TenantAccessService
from presentation.api.middleware.auth import get_current_user
from presentation.api.middleware.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="", tags=["Programmes"])


@router.post(
    "/",
    response_model=ProgrammeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new migration programme",
)
async def create_programme(
    body: CreateProgrammeRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> ProgrammeResponse:
    """Create a new SAP S/4HANA migration programme."""
    container = request.app.state.container
    use_case: CreateProgrammeUseCase = container.resolve(CreateProgrammeUseCase)
    return await use_case.execute(body)


@router.get(
    "/",
    response_model=ProgrammeListResponse,
    summary="List migration programmes",
)
async def list_programmes(
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
) -> ProgrammeListResponse:
    """List migration programmes belonging to the current tenant."""
    container = request.app.state.container
    query: ListProgrammesQuery = container.resolve(ListProgrammesQuery)
    return await query.execute(customer_id=tenant.customer_id)


@router.get(
    "/{programme_id}",
    response_model=ProgrammeResponse,
    summary="Get a migration programme by ID",
)
async def get_programme(
    programme_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
) -> ProgrammeResponse:
    """Retrieve a single migration programme by its unique identifier."""
    container = request.app.state.container

    # Validate tenant ownership before returning
    tenant_svc: TenantAccessService = container.resolve(TenantAccessService)
    try:
        programme = await tenant_svc.validate_programme_access(
            programme_id=programme_id,
            customer_id=tenant.customer_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programme {programme_id!r} not found",
        )
    return ProgrammeResponse.from_entity(programme)
