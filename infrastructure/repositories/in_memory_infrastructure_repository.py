"""InMemoryInfrastructurePlanRepository — dev-mode in-memory store for infrastructure plans."""

from __future__ import annotations

from datetime import datetime

from domain.entities.infrastructure_plan import InfrastructurePlan
from domain.value_objects.gcp_types import (
    AppServerConfig,
    CostEstimate,
    GCPMachineType,
    HANAConfig,
    NetworkConfig,
    SecurityConfig,
    ValidationStatus,
)


class InMemoryInfrastructurePlanRepository:
    """Implements InfrastructurePlanRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(plan: InfrastructurePlan) -> dict:
        hc = plan.hana_config
        ac = plan.app_server_config
        nc = plan.network_config
        sc = plan.security_config
        ce = plan.estimated_monthly_cost

        return {
            "id": plan.id,
            "programme_id": plan.programme_id,
            "region": plan.region,
            "dr_region": plan.dr_region,
            "hana_config": {
                "instance_type": hc.instance_type.value,
                "memory_gb": hc.memory_gb,
                "hana_data_disk_gb": hc.hana_data_disk_gb,
                "hana_log_disk_gb": hc.hana_log_disk_gb,
                "hana_shared_disk_gb": hc.hana_shared_disk_gb,
                "backup_disk_gb": hc.backup_disk_gb,
            },
            "app_server_config": {
                "instance_type": ac.instance_type.value,
                "instance_count": ac.instance_count,
                "auto_scaling": ac.auto_scaling,
                "min_instances": ac.min_instances,
                "max_instances": ac.max_instances,
            },
            "network_config": {
                "vpc_name": nc.vpc_name,
                "subnet_cidr_db": nc.subnet_cidr_db,
                "subnet_cidr_app": nc.subnet_cidr_app,
                "subnet_cidr_web": nc.subnet_cidr_web,
                "enable_cloud_nat": nc.enable_cloud_nat,
                "enable_private_google_access": nc.enable_private_google_access,
                "interconnect_bandwidth_gbps": nc.interconnect_bandwidth_gbps,
            },
            "ha_enabled": plan.ha_enabled,
            "dr_enabled": plan.dr_enabled,
            "security_config": {
                "enable_cmek": sc.enable_cmek,
                "enable_vpc_sc": sc.enable_vpc_sc,
                "enable_os_login": sc.enable_os_login,
                "enable_binary_auth": sc.enable_binary_auth,
                "kms_key_ring": sc.kms_key_ring,
            },
            "estimated_monthly_cost": {
                "hana_monthly": ce.hana_monthly,
                "app_server_monthly": ce.app_server_monthly,
                "storage_monthly": ce.storage_monthly,
                "network_monthly": ce.network_monthly,
                "backup_monthly": ce.backup_monthly,
                "monitoring_monthly": ce.monitoring_monthly,
                "cud_discount_percentage": ce.cud_discount_percentage,
            },
            "terraform_plan_ref": plan.terraform_plan_ref,
            "validation_status": plan.validation_status.value,
            "created_at": plan.created_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict) -> InfrastructurePlan:
        hc = data["hana_config"]
        ac = data["app_server_config"]
        nc = data["network_config"]
        sc = data["security_config"]
        ce = data["estimated_monthly_cost"]

        return InfrastructurePlan(
            id=data["id"],
            programme_id=data["programme_id"],
            region=data["region"],
            dr_region=data["dr_region"],
            hana_config=HANAConfig(
                instance_type=GCPMachineType(hc["instance_type"]),
                memory_gb=hc["memory_gb"],
                hana_data_disk_gb=hc["hana_data_disk_gb"],
                hana_log_disk_gb=hc["hana_log_disk_gb"],
                hana_shared_disk_gb=hc["hana_shared_disk_gb"],
                backup_disk_gb=hc["backup_disk_gb"],
            ),
            app_server_config=AppServerConfig(
                instance_type=GCPMachineType(ac["instance_type"]),
                instance_count=ac["instance_count"],
                auto_scaling=ac["auto_scaling"],
                min_instances=ac["min_instances"],
                max_instances=ac["max_instances"],
            ),
            network_config=NetworkConfig(
                vpc_name=nc["vpc_name"],
                subnet_cidr_db=nc["subnet_cidr_db"],
                subnet_cidr_app=nc["subnet_cidr_app"],
                subnet_cidr_web=nc["subnet_cidr_web"],
                enable_cloud_nat=nc["enable_cloud_nat"],
                enable_private_google_access=nc["enable_private_google_access"],
                interconnect_bandwidth_gbps=nc["interconnect_bandwidth_gbps"],
            ),
            ha_enabled=data["ha_enabled"],
            dr_enabled=data["dr_enabled"],
            security_config=SecurityConfig(
                enable_cmek=sc["enable_cmek"],
                enable_vpc_sc=sc["enable_vpc_sc"],
                enable_os_login=sc["enable_os_login"],
                enable_binary_auth=sc["enable_binary_auth"],
                kms_key_ring=sc["kms_key_ring"],
            ),
            estimated_monthly_cost=CostEstimate(
                hana_monthly=ce["hana_monthly"],
                app_server_monthly=ce["app_server_monthly"],
                storage_monthly=ce["storage_monthly"],
                network_monthly=ce["network_monthly"],
                backup_monthly=ce["backup_monthly"],
                monitoring_monthly=ce["monitoring_monthly"],
                cud_discount_percentage=ce["cud_discount_percentage"],
            ),
            terraform_plan_ref=data["terraform_plan_ref"],
            validation_status=ValidationStatus(data["validation_status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, plan: InfrastructurePlan) -> None:
        self._store[plan.id] = self._to_dict(plan)

    async def get_by_id(self, id: str) -> InfrastructurePlan | None:
        data = self._store.get(id)
        if data is None:
            return None
        return self._from_dict(data)

    async def list_by_programme(self, programme_id: str) -> list[InfrastructurePlan]:
        return [self._from_dict(data) for data in self._store.values() if data["programme_id"] == programme_id]

    async def get_latest_by_programme(self, programme_id: str) -> InfrastructurePlan | None:
        plans = [data for data in self._store.values() if data["programme_id"] == programme_id]
        if not plans:
            return None
        latest = max(plans, key=lambda d: d["created_at"])
        return self._from_dict(latest)
