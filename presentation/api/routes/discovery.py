"""Discovery routes — SAP landscape discovery intelligence endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from application.commands.generate_board_presentation import GenerateBoardPresentationUseCase
from application.commands.start_discovery import StartDiscoveryUseCase
from application.dtos.analysis_dto import DiscoveryResultsResponse
from application.queries.get_analysis_results import GetAnalysisResultsQuery
from domain.services.tenant_access_service import TenantAccessService
from presentation.api.middleware.tenant_context import TenantContext, get_tenant_context

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
    tenant: TenantContext = Depends(get_tenant_context),
) -> DiscoveryResultsResponse:
    """Trigger an AI-powered discovery run against the source SAP landscape.

    The request body should contain SAP connection parameters such as
    host, system_number, client, user, and password.
    """
    container = request.app.state.container

    # Validate tenant ownership before running discovery
    tenant_svc: TenantAccessService = container.resolve(TenantAccessService)
    try:
        await tenant_svc.validate_programme_access(
            programme_id=programme_id, customer_id=tenant.customer_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programme {programme_id!r} not found",
        )

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
    tenant: TenantContext = Depends(get_tenant_context),
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

    # Validate tenant ownership before returning results
    container = request.app.state.container
    tenant_svc: TenantAccessService = container.resolve(TenantAccessService)
    try:
        await tenant_svc.validate_programme_access(
            programme_id=programme_id, customer_id=tenant.customer_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programme {programme_id!r} not found",
        )

    query: GetAnalysisResultsQuery = container.resolve(GetAnalysisResultsQuery)
    result = await query.execute(programme_id=programme_id, landscape_id=landscape_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery results not found for programme {programme_id!r}",
        )
    return result


@router.get(
    "/{programme_id}/board-presentation",
    summary="Generate board-presentation scope document",
    responses={200: {"content": {"text/html": {}}}},
)
async def generate_board_presentation(
    programme_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
) -> Response:
    """Generate an HTML board-presentation scope document for download.

    Returns a self-contained HTML file with executive summary, complexity
    assessment, custom object inventory, risk register, and next steps.
    """
    container = request.app.state.container

    # Validate tenant ownership
    tenant_svc: TenantAccessService = container.resolve(TenantAccessService)
    try:
        await tenant_svc.validate_programme_access(
            programme_id=programme_id, customer_id=tenant.customer_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programme {programme_id!r} not found",
        )

    use_case: GenerateBoardPresentationUseCase = container.resolve(
        GenerateBoardPresentationUseCase
    )
    try:
        html_bytes = await use_case.execute(programme_id=programme_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return Response(
        content=html_bytes,
        media_type="text/html",
        headers={
            "Content-Disposition": (
                f'attachment; filename="board-presentation-{programme_id}.html"'
            ),
        },
    )
