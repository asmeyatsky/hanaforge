"""Data readiness routes — upload, profile, assess, and transform SAP table data."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from application.commands.assess_bp_consolidation import AssessBPConsolidationUseCase
from application.commands.assess_universal_journal import AssessUniversalJournalUseCase
from application.commands.generate_transformation_rules import GenerateTransformationRulesUseCase
from application.commands.run_data_profiling import RunDataProfilingUseCase
from application.commands.upload_data_export import UploadDataExportUseCase
from application.dtos.data_dto import (
    BPConsolidationResponse,
    DataProfilingResultsResponse,
    UniversalJournalResponse,
)
from application.queries.get_data_profiling_results import GetDataProfilingResultsQuery
from infrastructure.parsers.data_export_parser import DataExportParser
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["Data Readiness Engine"])

_parser = DataExportParser()


@router.post(
    "/upload/{landscape_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Upload SAP data export (CSV/XLSX/XML)",
)
async def upload_data_export(
    landscape_id: str,
    file: UploadFile,
    request: Request,
    _user=Depends(get_current_user),
) -> dict:
    """Upload an SAP table data export file for subsequent profiling."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    try:
        fmt = _parser.detect_format(file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    file_bytes = await file.read()
    container = request.app.state.container
    use_case: UploadDataExportUseCase = container.resolve(UploadDataExportUseCase)
    return await use_case.execute(
        landscape_id=landscape_id,
        file_bytes=file_bytes,
        filename=file.filename,
        format=fmt,
    )


@router.post(
    "/profile/{landscape_id}",
    response_model=DataProfilingResultsResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run data profiling on a landscape",
)
async def run_data_profiling(
    landscape_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> DataProfilingResultsResponse:
    """Trigger parallel data profiling for all uploaded tables in a landscape."""
    container = request.app.state.container
    use_case: RunDataProfilingUseCase = container.resolve(RunDataProfilingUseCase)
    return await use_case.execute(landscape_id=landscape_id)


@router.get(
    "/results/{landscape_id}",
    response_model=DataProfilingResultsResponse,
    summary="Get data profiling results",
)
async def get_profiling_results(
    landscape_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> DataProfilingResultsResponse:
    """Retrieve data profiling results for all tables in a landscape."""
    container = request.app.state.container
    query: GetDataProfilingResultsQuery = container.resolve(GetDataProfilingResultsQuery)
    return await query.execute(landscape_id=landscape_id)


@router.post(
    "/bp-consolidation/{landscape_id}",
    response_model=BPConsolidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess BP consolidation readiness",
)
async def assess_bp_consolidation(
    landscape_id: str,
    request: Request,
    customer_file: UploadFile | None = None,
    vendor_file: UploadFile | None = None,
    _user=Depends(get_current_user),
) -> BPConsolidationResponse:
    """Assess Customer/Vendor consolidation readiness for S/4HANA Business Partner model."""
    if customer_file is None or vendor_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both customer_file and vendor_file are required",
        )

    customer_bytes = await customer_file.read()
    vendor_bytes = await vendor_file.read()

    container = request.app.state.container
    use_case: AssessBPConsolidationUseCase = container.resolve(AssessBPConsolidationUseCase)
    result = await use_case.execute(
        landscape_id=landscape_id,
        customer_file_bytes=customer_bytes,
        vendor_file_bytes=vendor_bytes,
    )

    return BPConsolidationResponse(
        customer_count=result.customer_count,
        vendor_count=result.vendor_count,
        duplicate_pairs=result.duplicate_pairs,
        merge_candidates_count=len(result.merge_candidates),
        consolidation_complexity=result.consolidation_complexity,
    )


@router.post(
    "/universal-journal/{landscape_id}",
    response_model=UniversalJournalResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess Universal Journal migration readiness",
)
async def assess_universal_journal(
    landscape_id: str,
    request: Request,
    body: dict,
    _user=Depends(get_current_user),
) -> UniversalJournalResponse:
    """Assess ACDOCA migration readiness based on FI and CO configurations."""
    fi_config = body.get("fi_config", {})
    co_config = body.get("co_config", {})

    container = request.app.state.container
    use_case: AssessUniversalJournalUseCase = container.resolve(AssessUniversalJournalUseCase)
    result = await use_case.execute(
        landscape_id=landscape_id,
        fi_config=fi_config,
        co_config=co_config,
    )

    return UniversalJournalResponse(
        custom_coding_blocks=list(result.custom_coding_blocks),
        profit_centre_assignments=result.profit_centre_assignments,
        segment_reporting_configs=result.segment_reporting_configs,
        fi_gl_simplification_impact=result.fi_gl_simplification_impact,
        migration_complexity=result.migration_complexity,
    )


@router.post(
    "/transformation-rules/{landscape_id}/{table_name}",
    status_code=status.HTTP_200_OK,
    summary="Generate transformation rules for a table",
)
async def generate_transformation_rules(
    landscape_id: str,
    table_name: str,
    request: Request,
    _user=Depends(get_current_user),
) -> list[dict]:
    """Generate LTMC-compatible data transformation rules using AI."""
    container = request.app.state.container
    use_case: GenerateTransformationRulesUseCase = container.resolve(GenerateTransformationRulesUseCase)

    try:
        rules = await use_case.execute(
            landscape_id=landscape_id,
            table_name=table_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return [
        {
            "source_field": rule.source_field,
            "target_field": rule.target_field,
            "rule_type": rule.rule_type.value,
            "rule_expression": rule.rule_expression,
            "description": rule.description,
        }
        for rule in rules
    ]
