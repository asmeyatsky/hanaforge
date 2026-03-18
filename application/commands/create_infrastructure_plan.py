"""CreateInfrastructurePlanUseCase — creates a GCP SAP landing zone plan.

Orchestrates Quick Sizer parsing, sizing service, cost estimation, validation,
and persistence. HANA and app server sizing run as independent domain operations
that could be parallelised at the orchestration layer.
"""

from __future__ import annotations

import asyncio
import base64
import uuid

from application.dtos.infrastructure_dto import (
    CreateInfrastructurePlanRequest,
    InfrastructurePlanResponse,
)
from domain.entities.infrastructure_plan import InfrastructurePlan
from domain.ports.event_bus_ports import EventBusPort
from domain.ports.infrastructure_ports import (
    InfrastructurePlanRepositoryPort,
    QuickSizerParserPort,
)
from domain.services.plan_validation_service import PlanValidationService
from domain.services.sizing_service import SAPSizingService
from domain.value_objects.gcp_types import (
    GCPRegion,
    NetworkConfig,
    SecurityConfig,
    SizingInput,
)
from domain.value_objects.object_type import SystemRole


class CreateInfrastructurePlanUseCase:
    """Single-responsibility use case: create and validate a GCP infrastructure plan."""

    def __init__(
        self,
        repository: InfrastructurePlanRepositoryPort,
        event_bus: EventBusPort,
        quick_sizer_parser: QuickSizerParserPort,
        sizing_service: SAPSizingService | None = None,
        validation_service: PlanValidationService | None = None,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._quick_sizer_parser = quick_sizer_parser
        self._sizing = sizing_service or SAPSizingService()
        self._validation = validation_service or PlanValidationService()

    async def execute(
        self,
        programme_id: str,
        request: CreateInfrastructurePlanRequest,
    ) -> InfrastructurePlanResponse:
        # 1. Parse sizing input — Quick Sizer XML takes priority over manual
        sizing = await self._resolve_sizing(request)

        # 2. Resolve GCP region enum
        region = self._resolve_region(request.region)

        # 3. HANA and app server sizing (independent — fan out)
        hana_config, app_config = await asyncio.gather(
            asyncio.to_thread(self._sizing.recommend_hana_config, sizing),
            asyncio.to_thread(
                self._sizing.recommend_app_server_config,
                sizing.saps_rating,
                sizing.concurrent_users,
                sizing.landscape_type,
            ),
        )

        # 4. Network config — deterministic from programme context
        network_config = NetworkConfig(
            vpc_name=f"sap-vpc-{programme_id[:8]}",
            subnet_cidr_db="10.0.1.0/24",
            subnet_cidr_app="10.0.2.0/24",
            subnet_cidr_web="10.0.3.0/24",
            enable_cloud_nat=True,
            enable_private_google_access=True,
            interconnect_bandwidth_gbps=None,
        )

        # 5. Security config — CMEK and VPC-SC enabled for PRD
        is_production = sizing.landscape_type == SystemRole.PRD
        security_config = SecurityConfig(
            enable_cmek=is_production,
            enable_vpc_sc=is_production,
            enable_os_login=True,
            enable_binary_auth=is_production,
            kms_key_ring=f"sap-kms-{programme_id[:8]}" if is_production else None,
        )

        # 6. Cost estimate
        cost_estimate = self._sizing.calculate_cost_estimate(
            hana=hana_config,
            app=app_config,
            region=region,
            ha_enabled=request.ha_enabled,
            dr_enabled=request.dr_enabled,
        )

        # 7. Create aggregate
        plan = InfrastructurePlan.create(
            id=str(uuid.uuid4()),
            programme_id=programme_id,
            region=request.region,
            dr_region=request.dr_region,
            hana_config=hana_config,
            app_server_config=app_config,
            network_config=network_config,
            ha_enabled=request.ha_enabled,
            dr_enabled=request.dr_enabled,
            security_config=security_config,
            estimated_monthly_cost=cost_estimate,
        )

        # 8. Validate against SAP certification
        validation_result = self._validation.validate_sap_certification(plan)
        plan = plan.validate_plan(validation_result)

        # 9. Persist and publish events
        await self._repository.save(plan)
        if plan.domain_events:
            await self._event_bus.publish(list(plan.domain_events))

        return InfrastructurePlanResponse.from_entity(plan)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_sizing(self, request: CreateInfrastructurePlanRequest) -> SizingInput:
        if request.quick_sizer_xml_base64 is not None:
            xml_bytes = base64.b64decode(request.quick_sizer_xml_base64)
            return await self._quick_sizer_parser.parse_quick_sizer_xml(xml_bytes)

        if request.sizing_input is not None:
            return SizingInput(
                saps_rating=request.sizing_input.saps_rating,
                hana_memory_gb=request.sizing_input.hana_memory_gb,
                db_size_gb=request.sizing_input.db_size_gb,
                concurrent_users=request.sizing_input.concurrent_users,
                landscape_type=SystemRole(request.sizing_input.landscape_type),
            )

        raise ValueError("Either sizing_input or quick_sizer_xml_base64 must be provided.")

    @staticmethod
    def _resolve_region(region_str: str) -> GCPRegion:
        try:
            return GCPRegion(region_str)
        except ValueError:
            # Attempt enum name match (e.g. "US_CENTRAL1")
            try:
                return GCPRegion[region_str.upper()]
            except KeyError:
                raise ValueError(f"Unsupported GCP region: {region_str!r}. Supported: {[r.value for r in GCPRegion]}")
