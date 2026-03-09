"""Programme routes — CRUD endpoints for migration programmes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from application.commands.create_programme import CreateProgrammeUseCase
from application.dtos.programme_dto import (
    CreateProgrammeRequest,
    ProgrammeListResponse,
    ProgrammeResponse,
)
from application.queries.get_programme import GetProgrammeQuery
from application.queries.list_programmes import ListProgrammesQuery
from presentation.api.middleware.auth import get_current_user

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
    customer_id: str | None = None,
    _user=Depends(get_current_user),
) -> ProgrammeListResponse:
    """List all migration programmes, optionally filtered by customer ID."""
    container = request.app.state.container
    query: ListProgrammesQuery = container.resolve(ListProgrammesQuery)
    return await query.execute(customer_id=customer_id)


@router.get(
    "/{programme_id}",
    response_model=ProgrammeResponse,
    summary="Get a migration programme by ID",
)
async def get_programme(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> ProgrammeResponse:
    """Retrieve a single migration programme by its unique identifier."""
    container = request.app.state.container
    query: GetProgrammeQuery = container.resolve(GetProgrammeQuery)
    result = await query.execute(programme_id=programme_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programme {programme_id!r} not found",
        )
    return result
