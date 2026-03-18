"""ABAP analysis routes — upload, analyse, and retrieve ABAP code intelligence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response

from application.commands.export_remediation_backlog import ExportRemediationBacklogUseCase
from application.commands.run_abap_analysis import RunABAPAnalysisUseCase
from application.commands.upload_abap_source import UploadABAPSourceUseCase
from application.dtos.analysis_dto import AnalysisResultsResponse
from application.queries.get_analysis_results import GetAnalysisResultsQuery
from domain.ports.remediation_export_ports import RemediationExportFormat
from domain.services.tenant_access_service import TenantAccessService
from presentation.api.middleware.auth import get_current_user
from presentation.api.middleware.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="", tags=["ABAP Code Intelligence"])


@router.post(
    "/upload/{landscape_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Upload ABAP source ZIP for a landscape",
)
async def upload_abap_source(
    landscape_id: str,
    file: UploadFile,
    request: Request,
    _user=Depends(get_current_user),
) -> dict:
    """Upload a ZIP archive containing ABAP source files for analysis.

    The file is stored in the artefact bucket and indexed for subsequent
    analysis runs.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip files are accepted",
        )

    file_bytes = await file.read()
    container = request.app.state.container
    use_case: UploadABAPSourceUseCase = container.resolve(UploadABAPSourceUseCase)
    return await use_case.execute(
        landscape_id=landscape_id,
        file_bytes=file_bytes,
        filename=file.filename,
    )


@router.post(
    "/analyze/{landscape_id}",
    response_model=AnalysisResultsResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run ABAP code analysis on a landscape",
)
async def run_abap_analysis(
    landscape_id: str,
    request: Request,
    programme_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
) -> AnalysisResultsResponse:
    """Trigger AI-powered ABAP compatibility analysis for all objects
    uploaded to the given landscape.
    """
    container = request.app.state.container

    # Validate tenant ownership of the programme before running analysis
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

    use_case: RunABAPAnalysisUseCase = container.resolve(RunABAPAnalysisUseCase)
    return await use_case.execute(landscape_id=landscape_id, programme_id=programme_id)


@router.get(
    "/results/{programme_id}/{landscape_id}",
    response_model=AnalysisResultsResponse,
    summary="Get ABAP analysis results",
)
async def get_analysis_results(
    programme_id: str,
    landscape_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
) -> AnalysisResultsResponse:
    """Retrieve the ABAP analysis results for a specific programme and landscape."""
    container = request.app.state.container

    # Validate tenant ownership before returning results
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
            detail=(
                f"Analysis results not found for programme {programme_id!r} "
                f"and landscape {landscape_id!r}"
            ),
        )
    return result


# ------------------------------------------------------------------
# Content-type / file extension mapping for remediation export
# ------------------------------------------------------------------

_FORMAT_CONTENT_TYPES: dict[RemediationExportFormat, tuple[str, str]] = {
    RemediationExportFormat.JIRA: ("application/json", "remediation_backlog.json"),
    RemediationExportFormat.AZURE_DEVOPS: ("text/csv", "remediation_backlog_ado.csv"),
    RemediationExportFormat.CSV: ("text/csv", "remediation_backlog.csv"),
}


@router.get(
    "/export/{landscape_id}",
    summary="Export remediation backlog for a landscape",
)
async def export_remediation_backlog(
    landscape_id: str,
    request: Request,
    format: str = Query("csv", description="Export format: jira, azure_devops, or csv"),
    _user=Depends(get_current_user),
) -> Response:
    """Export all remediation suggestions for a landscape as a downloadable file.

    Supported formats: ``jira`` (JSON), ``azure_devops`` (CSV), ``csv`` (generic CSV).
    """
    try:
        export_format = RemediationExportFormat(format.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported format {format!r}. "
                f"Supported: {', '.join(f.value.lower() for f in RemediationExportFormat)}"
            ),
        )

    container = request.app.state.container
    use_case: ExportRemediationBacklogUseCase = container.resolve(
        ExportRemediationBacklogUseCase
    )
    data = await use_case.execute(landscape_id=landscape_id, format=export_format)

    content_type, filename = _FORMAT_CONTENT_TYPES[export_format]
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
