"""TestForge SAP Edition routes — test generation, export, and traceability endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

from application.commands.export_test_scenarios import ExportTestScenariosUseCase
from application.commands.generate_interface_tests import GenerateInterfaceTestsUseCase
from application.commands.generate_test_scenarios import GenerateTestScenariosUseCase
from application.dtos.test_dto import (
    ExportRequest,
    TestGenerationResponse,
    TestResultsResponse,
    TraceabilityMatrixResponse,
)
from application.queries.get_test_results import GetTestResultsQuery
from application.queries.get_traceability_matrix import GetTraceabilityMatrixQuery
from domain.value_objects.test_types import ProcessArea, TestExportFormat
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["TestForge SAP Edition"])


# ------------------------------------------------------------------
# Request models (inline to keep route file self-contained)
# ------------------------------------------------------------------


class GenerateTestsRequest(BaseModel):
    process_area: str | None = None
    process_definitions: list[dict]
    sap_version: str = "S/4HANA 2023"


class GenerateInterfaceTestsRequest(BaseModel):
    interfaces: list[dict]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post(
    "/generate/{programme_id}",
    response_model=TestGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate test scenarios for SAP business processes",
)
async def generate_test_scenarios(
    programme_id: str,
    body: GenerateTestsRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> TestGenerationResponse:
    """Generate end-to-end test scenarios for the specified programme and process area."""
    container = request.app.state.container
    use_case: GenerateTestScenariosUseCase = container.resolve(GenerateTestScenariosUseCase)
    area = ProcessArea(body.process_area) if body.process_area else None
    return await use_case.execute(
        programme_id=programme_id,
        process_area=area,
        process_definitions=body.process_definitions,
        sap_version=body.sap_version,
    )


@router.post(
    "/generate-interface-tests/{programme_id}",
    response_model=TestGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate interface test cases for IDoc/RFC/BAPI",
)
async def generate_interface_tests(
    programme_id: str,
    body: GenerateInterfaceTestsRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> TestGenerationResponse:
    """Generate test cases for each IDoc, RFC, BAPI, REST, or OData interface."""
    container = request.app.state.container
    use_case: GenerateInterfaceTestsUseCase = container.resolve(GenerateInterfaceTestsUseCase)
    return await use_case.execute(
        programme_id=programme_id,
        interfaces=body.interfaces,
    )


@router.get(
    "/scenarios/{programme_id}",
    response_model=TestResultsResponse,
    summary="List test scenarios for a programme",
)
async def list_test_scenarios(
    programme_id: str,
    request: Request,
    process_area: str | None = None,
    _user=Depends(get_current_user),
) -> TestResultsResponse:
    """Retrieve test scenarios and status summary, optionally filtered by process area."""
    container = request.app.state.container
    query: GetTestResultsQuery = container.resolve(GetTestResultsQuery)
    area = ProcessArea(process_area) if process_area else None
    return await query.execute(programme_id=programme_id, process_area=area)


@router.get(
    "/traceability/{programme_id}",
    response_model=TraceabilityMatrixResponse,
    summary="Get traceability matrix for a programme",
)
async def get_traceability_matrix(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> TraceabilityMatrixResponse:
    """Retrieve the traceability matrix mapping processes to test cases and defects."""
    container = request.app.state.container
    query: GetTraceabilityMatrixQuery = container.resolve(GetTraceabilityMatrixQuery)
    return await query.execute(programme_id=programme_id)


@router.post(
    "/export/{programme_id}",
    summary="Export test scenarios to a test management tool format",
)
async def export_test_scenarios(
    programme_id: str,
    body: ExportRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> Response:
    """Export tests to HP ALM, Tricentis Tosca, Azure DevOps, Jira Xray, or CSV."""
    container = request.app.state.container
    use_case: ExportTestScenariosUseCase = container.resolve(ExportTestScenariosUseCase)
    export_format = TestExportFormat(body.format)
    area = ProcessArea(body.process_area) if body.process_area else None

    file_bytes = await use_case.execute(
        programme_id=programme_id,
        format=export_format,
        process_area=area,
    )

    # Set content type based on format
    content_types = {
        TestExportFormat.JIRA_XRAY: "application/json",
        TestExportFormat.AZURE_DEVOPS: "text/csv",
        TestExportFormat.HP_ALM: "application/xml",
        TestExportFormat.TRICENTIS_TOSCA: "application/xml",
        TestExportFormat.CSV: "text/csv",
    }
    content_type = content_types.get(export_format, "application/octet-stream")

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename=tests.{body.format.lower()}"},
    )
