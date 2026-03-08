"""Discovery routes — SAP landscape discovery intelligence endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from application.commands.start_discovery import StartDiscoveryUseCase
from application.dtos.analysis_dto import DiscoveryResultsResponse
from application.queries.get_analysis_results import GetAnalysisResultsQuery
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["Discovery Intelligence"])


@router.post(
    "/{programme_id}/discover",
    response_model=DiscoveryResultsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start SAP landscape discovery",
)
async def start_discovery(
    programme_id: str,
    body: dict[str, Any],
    request: Request,
    _user: dict[str, str] = Depends(get_current_user),
) -> DiscoveryResultsResponse:
    """Trigger an AI-powered discovery run against the source SAP landscape.

    The request body should contain SAP connection parameters such as
    host, system_number, client, user, and password.
    """
    container = request.app.state.container
    use_case: StartDiscoveryUseCase = container.resolve(StartDiscoveryUseCase)
    return await use_case.execute(programme_id=programme_id, connection_params=body)


@router.get(
    "/{programme_id}/landscape",
    response_model=DiscoveryResultsResponse,
    summary="Get discovery results for a programme",
)
async def get_discovery_results(
    programme_id: str,
    request: Request,
    landscape_id: str | None = None,
    _user: dict[str, str] = Depends(get_current_user),
) -> DiscoveryResultsResponse:
    """Retrieve the latest discovery results for a given programme.

    If landscape_id is provided, returns results for that specific landscape;
    otherwise returns the most recent discovery run.
    """
    if landscape_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="landscape_id query parameter is required",
        )
    container = request.app.state.container
    query: GetAnalysisResultsQuery = container.resolve(GetAnalysisResultsQuery)
    result = await query.execute(programme_id=programme_id, landscape_id=landscape_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery results not found for programme {programme_id!r}",
        )
    return result
