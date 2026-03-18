"""GenerateTerraformUseCase — generates and validates Terraform HCL for a plan.

Orchestrates Terraform generation, SAP certification validation, and plan update.
The HCL generation and domain validation are independent and can run concurrently.
"""

from __future__ import annotations

import asyncio
import uuid

from application.dtos.infrastructure_dto import (
    TerraformResponse,
    ValidationResultResponse,
)
from domain.ports.event_bus_ports import EventBusPort
from domain.ports.infrastructure_ports import (
    InfrastructurePlanRepositoryPort,
    TerraformGeneratorPort,
)
from domain.services.plan_validation_service import PlanValidationService


class GenerateTerraformUseCase:
    """Single-responsibility use case: generate Terraform HCL and validate the plan."""

    def __init__(
        self,
        repository: InfrastructurePlanRepositoryPort,
        terraform_generator: TerraformGeneratorPort,
        event_bus: EventBusPort,
        validation_service: PlanValidationService | None = None,
    ) -> None:
        self._repository = repository
        self._terraform = terraform_generator
        self._event_bus = event_bus
        self._validation = validation_service or PlanValidationService()

    async def execute(self, plan_id: str) -> TerraformResponse:
        # 1. Load plan
        plan = await self._repository.get_by_id(plan_id)
        if plan is None:
            raise ValueError(f"Infrastructure plan {plan_id!r} not found.")

        # 2. Generate HCL and validate concurrently
        hcl, domain_validation = await asyncio.gather(
            self._terraform.generate_plan(plan),
            asyncio.to_thread(
                self._validation.validate_sap_certification, plan
            ),
        )

        # 3. Validate the generated HCL itself
        hcl_validation = await self._terraform.validate_plan(hcl)

        # 4. Use the stricter of the two validation results
        final_validation = (
            hcl_validation
            if hcl_validation.checks_failed > domain_validation.checks_failed
            else domain_validation
        )

        # 5. Store Terraform reference and update plan
        plan_ref = f"gs://hanaforge-terraform/{plan.programme_id}/{plan_id}/{uuid.uuid4().hex[:8]}.tf"
        plan = plan.mark_terraform_generated(plan_ref)
        plan = plan.validate_plan(final_validation)

        # 6. Persist and publish events
        await self._repository.save(plan)
        if plan.domain_events:
            await self._event_bus.publish(list(plan.domain_events))

        return TerraformResponse(
            plan_id=plan_id,
            hcl_content=hcl,
            validation=ValidationResultResponse(
                status=final_validation.status.value,
                checks_passed=final_validation.checks_passed,
                checks_failed=final_validation.checks_failed,
                warnings=list(final_validation.warnings),
                errors=list(final_validation.errors),
            ),
        )
