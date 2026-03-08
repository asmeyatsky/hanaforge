"""ABAP analysis routes — upload, analyse, and retrieve ABAP code intelligence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from application.commands.run_abap_analysis import RunABAPAnalysisUseCase
from application.commands.upload_abap_source import UploadABAPSourceUseCase
from application.dtos.analysis_dto import AnalysisResultsResponse
from application.queries.get_analysis_results import GetAnalysisResultsQuery
from presentation.api.middleware.auth import get_current_user

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
    _user: dict[str, str] = Depends(get_current_user),
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
    _user: dict[str, str] = Depends(get_current_user),
) -> AnalysisResultsResponse:
    """Trigger AI-powered ABAP compatibility analysis for all objects
    uploaded to the given landscape.
    """
    container = request.app.state.container
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
    _user: dict[str, str] = Depends(get_current_user),
) -> AnalysisResultsResponse:
    """Retrieve the ABAP analysis results for a specific programme and landscape."""
    container = request.app.state.container
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
