"""InfrastructurePlan aggregate root — GCP SAP landing zone configuration.

Architectural Intent:
- Immutable aggregate managing the lifecycle of a GCP infrastructure plan
- State transitions produce new instances with domain events collected
- Validation, Terraform generation, and approval are explicit state changes
- All business invariants enforced within the aggregate boundary
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from domain.events.event_base import DomainEvent
from domain.events.infrastructure_events import (
    InfrastructurePlanCreatedEvent,
    PlanValidatedEvent,
    TerraformPlanGeneratedEvent,
)
from domain.value_objects.gcp_types import (
    AppServerConfig,
    CostEstimate,
    HANAConfig,
    NetworkConfig,
    SecurityConfig,
    ValidationResult,
    ValidationStatus,
)


@dataclass(frozen=True)
class InfrastructurePlan:
    """Aggregate root representing a complete GCP SAP landing zone plan."""

    id: str
    programme_id: str
    region: str
    dr_region: str | None
    hana_config: HANAConfig
    app_server_config: AppServerConfig
    network_config: NetworkConfig
    ha_enabled: bool
    dr_enabled: bool
    security_config: SecurityConfig
    estimated_monthly_cost: CostEstimate
    terraform_plan_ref: str | None
    validation_status: ValidationStatus
    created_at: datetime
    domain_events: tuple[DomainEvent, ...] = field(default=())

    # ------------------------------------------------------------------
    # Behaviour — each method returns a new immutable instance
    # ------------------------------------------------------------------

    def validate_plan(self, result: ValidationResult) -> InfrastructurePlan:
        """Apply validation result and emit a PlanValidatedEvent."""
        new_status = result.status
        event = PlanValidatedEvent(
            aggregate_id=self.id,
            programme_id=self.programme_id,
            status=new_status.value,
            checks_passed=result.checks_passed,
            checks_failed=result.checks_failed,
        )
        return replace(
            self,
            validation_status=new_status,
            domain_events=(*self.domain_events, event),
        )

    def mark_terraform_generated(self, ref: str) -> InfrastructurePlan:
        """Record that Terraform HCL has been generated and stored at *ref*."""
        event = TerraformPlanGeneratedEvent(
            aggregate_id=self.id,
            programme_id=self.programme_id,
            plan_ref=ref,
        )
        return replace(
            self,
            terraform_plan_ref=ref,
            domain_events=(*self.domain_events, event),
        )

    def approve_plan(self) -> InfrastructurePlan:
        """Mark the plan as approved — validation must have passed or have warnings."""
        if self.validation_status not in (
            ValidationStatus.PASSED,
            ValidationStatus.WARNINGS,
        ):
            raise ValueError(
                f"Cannot approve plan with validation status "
                f"{self.validation_status.value}. Must be PASSED or WARNINGS."
            )
        return replace(self, validation_status=ValidationStatus.PASSED)

    def update_cost_estimate(self, cost: CostEstimate) -> InfrastructurePlan:
        """Replace the cost estimate with an updated calculation."""
        return replace(self, estimated_monthly_cost=cost)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def create(
        *,
        id: str,
        programme_id: str,
        region: str,
        dr_region: str | None,
        hana_config: HANAConfig,
        app_server_config: AppServerConfig,
        network_config: NetworkConfig,
        ha_enabled: bool,
        dr_enabled: bool,
        security_config: SecurityConfig,
        estimated_monthly_cost: CostEstimate,
    ) -> InfrastructurePlan:
        """Create a new plan with an InfrastructurePlanCreatedEvent."""
        now = datetime.now(timezone.utc)
        event = InfrastructurePlanCreatedEvent(
            aggregate_id=id,
            programme_id=programme_id,
            region=region,
        )
        return InfrastructurePlan(
            id=id,
            programme_id=programme_id,
            region=region,
            dr_region=dr_region,
            hana_config=hana_config,
            app_server_config=app_server_config,
            network_config=network_config,
            ha_enabled=ha_enabled,
            dr_enabled=dr_enabled,
            security_config=security_config,
            estimated_monthly_cost=estimated_monthly_cost,
            terraform_plan_ref=None,
            validation_status=ValidationStatus.NOT_VALIDATED,
            created_at=now,
            domain_events=(event,),
        )
