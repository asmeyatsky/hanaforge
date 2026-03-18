"""Infrastructure DTOs — Pydantic models for API serialization of GCP provisioning."""

from __future__ import annotations

from pydantic import BaseModel, Field

from domain.entities.infrastructure_plan import InfrastructurePlan

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class SizingInputRequest(BaseModel):
    """Manual sizing parameters when Quick Sizer XML is not available."""

    saps_rating: int = Field(gt=0, description="SAP Application Performance Standard rating")
    hana_memory_gb: int = Field(gt=0, description="Required HANA memory in GB")
    db_size_gb: float = Field(gt=0, description="Current database size in GB")
    concurrent_users: int = Field(gt=0, description="Peak concurrent user count")
    landscape_type: str = Field(description="System role: DEV, QAS, or PRD")


class CreateInfrastructurePlanRequest(BaseModel):
    """Request payload to create a new GCP infrastructure plan."""

    sizing_input: SizingInputRequest | None = None
    quick_sizer_xml_base64: str | None = None
    region: str
    dr_region: str | None = None
    ha_enabled: bool = True
    dr_enabled: bool = False


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class HANAConfigResponse(BaseModel):
    """HANA instance configuration details."""

    instance_type: str
    memory_gb: int
    hana_data_disk_gb: int
    hana_log_disk_gb: int
    hana_shared_disk_gb: int
    backup_disk_gb: int


class AppServerConfigResponse(BaseModel):
    """Application server configuration details."""

    instance_type: str
    instance_count: int
    auto_scaling: bool
    min_instances: int
    max_instances: int


class CostEstimateResponse(BaseModel):
    """Monthly GCP cost breakdown with CUD optimisation."""

    hana_monthly: float
    app_server_monthly: float
    storage_monthly: float
    network_monthly: float
    backup_monthly: float
    monitoring_monthly: float
    total_monthly: float
    total_annual: float
    cud_discount_percentage: float
    cud_monthly: float


class ValidationResultResponse(BaseModel):
    """SAP certification validation result."""

    status: str
    checks_passed: int
    checks_failed: int
    warnings: list[str]
    errors: list[str]


class InfrastructurePlanResponse(BaseModel):
    """Serialisable representation of an InfrastructurePlan entity."""

    id: str
    programme_id: str
    region: str
    dr_region: str | None
    hana_config: HANAConfigResponse
    app_server_config: AppServerConfigResponse
    ha_enabled: bool
    dr_enabled: bool
    cost_estimate: CostEstimateResponse
    validation_status: str
    terraform_available: bool
    created_at: str

    @staticmethod
    def from_entity(plan: InfrastructurePlan) -> InfrastructurePlanResponse:
        cost = plan.estimated_monthly_cost
        return InfrastructurePlanResponse(
            id=plan.id,
            programme_id=plan.programme_id,
            region=plan.region,
            dr_region=plan.dr_region,
            hana_config=HANAConfigResponse(
                instance_type=plan.hana_config.instance_type.value,
                memory_gb=plan.hana_config.memory_gb,
                hana_data_disk_gb=plan.hana_config.hana_data_disk_gb,
                hana_log_disk_gb=plan.hana_config.hana_log_disk_gb,
                hana_shared_disk_gb=plan.hana_config.hana_shared_disk_gb,
                backup_disk_gb=plan.hana_config.backup_disk_gb,
            ),
            app_server_config=AppServerConfigResponse(
                instance_type=plan.app_server_config.instance_type.value,
                instance_count=plan.app_server_config.instance_count,
                auto_scaling=plan.app_server_config.auto_scaling,
                min_instances=plan.app_server_config.min_instances,
                max_instances=plan.app_server_config.max_instances,
            ),
            ha_enabled=plan.ha_enabled,
            dr_enabled=plan.dr_enabled,
            cost_estimate=CostEstimateResponse(
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
            ),
            validation_status=plan.validation_status.value,
            terraform_available=plan.terraform_plan_ref is not None,
            created_at=plan.created_at.isoformat(),
        )


class TerraformResponse(BaseModel):
    """Generated Terraform HCL with validation results."""

    plan_id: str
    hcl_content: str
    validation: ValidationResultResponse
