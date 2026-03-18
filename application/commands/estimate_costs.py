"""EstimateCostsUseCase — calculates GCP costs across all SAP landscapes.

Produces a consolidated cost view for DEV/QAS/PRD and optional DR,
applying appropriate CUD discount optimisation per landscape tier.
"""

from __future__ import annotations

from application.dtos.infrastructure_dto import CostEstimateResponse
from domain.ports.infrastructure_ports import InfrastructurePlanRepositoryPort
from domain.services.sizing_service import SAPSizingService
from domain.value_objects.gcp_types import GCPRegion


class EstimateCostsUseCase:
    """Single-responsibility use case: calculate cost estimate for a programme."""

    def __init__(
        self,
        repository: InfrastructurePlanRepositoryPort,
        sizing_service: SAPSizingService | None = None,
    ) -> None:
        self._repository = repository
        self._sizing = sizing_service or SAPSizingService()

    async def execute(self, programme_id: str) -> CostEstimateResponse:
        plan = await self._repository.get_latest_by_programme(programme_id)
        if plan is None:
            raise ValueError(f"No infrastructure plan found for programme {programme_id!r}.")

        # Recalculate cost from current plan state
        try:
            region = GCPRegion(plan.region)
        except ValueError:
            try:
                region = GCPRegion[plan.region.upper()]
            except KeyError:
                region = GCPRegion.US_CENTRAL1

        cost = self._sizing.calculate_cost_estimate(
            hana=plan.hana_config,
            app=plan.app_server_config,
            region=region,
            ha_enabled=plan.ha_enabled,
            dr_enabled=plan.dr_enabled,
        )

        return CostEstimateResponse(
            hana_monthly=cost.hana_monthly,
            app_server_monthly=cost.app_server_monthly,
            storage_monthly=cost.storage_monthly,
            network_monthly=cost.network_monthly,
            backup_monthly=cost.backup_monthly,
            monitoring_monthly=cost.monitoring_monthly,
            total_monthly=cost.total_monthly,
            total_annual=cost.total_annual,
            cud_discount_percentage=cost.cud_discount_percentage,
            cud_monthly=cost.cud_monthly,
        )
