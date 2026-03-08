"""Infrastructure routes — GCP provisioning endpoints for SAP landing zones."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from application.commands.create_infrastructure_plan import (
    CreateInfrastructurePlanUseCase,
)
from application.commands.estimate_costs import EstimateCostsUseCase
from application.commands.generate_terraform import GenerateTerraformUseCase
from application.dtos.infrastructure_dto import (
    CostEstimateResponse,
    CreateInfrastructurePlanRequest,
    InfrastructurePlanResponse,
    TerraformResponse,
    ValidationResultResponse,
)
from application.queries.get_infrastructure_plan import GetInfrastructurePlanQuery
from domain.services.plan_validation_service import PlanValidationService
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["GCP Infrastructure Provisioner"])


@router.post(
    "/plan/{programme_id}",
    response_model=InfrastructurePlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a GCP infrastructure plan",
)
async def create_plan(
    programme_id: str,
    body: CreateInfrastructurePlanRequest,
    request: Request,
    _user: dict[str, str] = Depends(get_current_user),
) -> InfrastructurePlanResponse:
    """Create a new GCP infrastructure plan for an SAP S/4HANA migration programme."""
    container = request.app.state.container
    use_case: CreateInfrastructurePlanUseCase = container.resolve(
        "CreateInfrastructurePlanUseCase"
    )
    try:
        return await use_case.execute(programme_id=programme_id, request=body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/plan/{programme_id}",
    response_model=InfrastructurePlanResponse,
    summary="Get the current infrastructure plan",
)
async def get_plan(
    programme_id: str,
    request: Request,
    _user: dict[str, str] = Depends(get_current_user),
) -> InfrastructurePlanResponse:
    """Retrieve the latest infrastructure plan for a programme."""
    container = request.app.state.container
    query: GetInfrastructurePlanQuery = container.resolve(
        "GetInfrastructurePlanQuery"
    )
    result = await query.execute(programme_id=programme_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No infrastructure plan found for programme {programme_id!r}",
        )
    return result


@router.post(
    "/terraform/{plan_id}",
    response_model=TerraformResponse,
    summary="Generate Terraform HCL",
)
async def generate_terraform(
    plan_id: str,
    request: Request,
    _user: dict[str, str] = Depends(get_current_user),
) -> TerraformResponse:
    """Generate complete Terraform HCL for a previously created infrastructure plan."""
    container = request.app.state.container
    use_case: GenerateTerraformUseCase = container.resolve(
        "GenerateTerraformUseCase"
    )
    try:
        return await use_case.execute(plan_id=plan_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/costs/{programme_id}",
    response_model=CostEstimateResponse,
    summary="Get cost estimate",
)
async def get_costs(
    programme_id: str,
    request: Request,
    _user: dict[str, str] = Depends(get_current_user),
) -> CostEstimateResponse:
    """Calculate monthly GCP cost estimate for a programme."""
    container = request.app.state.container
    use_case: EstimateCostsUseCase = container.resolve("EstimateCostsUseCase")
    try:
        return await use_case.execute(programme_id=programme_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "/validate/{plan_id}",
    response_model=ValidationResultResponse,
    summary="Validate plan against SAP certification",
)
async def validate_plan(
    plan_id: str,
    request: Request,
    _user: dict[str, str] = Depends(get_current_user),
) -> ValidationResultResponse:
    """Validate an infrastructure plan against SAP on GCP certification requirements."""
    container = request.app.state.container
    repo = container.resolve("InfrastructurePlanRepositoryPort")
    plan = await repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Infrastructure plan {plan_id!r} not found",
        )

    validation_service = PlanValidationService()
    result = validation_service.validate_sap_certification(plan)

    return ValidationResultResponse(
        status=result.status.value,
        checks_passed=result.checks_passed,
        checks_failed=result.checks_failed,
        warnings=list(result.warnings),
        errors=list(result.errors),
    )
