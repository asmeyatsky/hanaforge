"""SAP sizing service — pure domain logic that maps Quick Sizer outputs to GCP resources.

Architectural Intent:
- Stateless service containing SAP-to-GCP sizing rules
- Pricing table uses approximate GCP on-demand rates (2026)
- CUD discounts applied at 1-year (20%) or 3-year (37%) committed-use levels
- No infrastructure dependencies — operates purely on domain value objects

Parallelization Notes:
- HANA sizing and app server sizing are independent and can run concurrently
- Cost calculation depends on both configs being available first
"""

from __future__ import annotations

from domain.value_objects.gcp_types import (
    AppServerConfig,
    CostEstimate,
    GCPMachineType,
    GCPRegion,
    HANAConfig,
    SizingInput,
)
from domain.value_objects.object_type import SystemRole

# ---------------------------------------------------------------------------
# Approximate on-demand monthly pricing (USD) per machine type
# Source: GCP pricing calculator, rounded for estimation purposes
# ---------------------------------------------------------------------------

_MACHINE_MONTHLY_COST: dict[GCPMachineType, float] = {
    # M3 Ultra — memory-optimised HANA
    GCPMachineType.M3_ULTRAMEM_32: 6_835.00,
    GCPMachineType.M3_ULTRAMEM_64: 13_670.00,
    GCPMachineType.M3_ULTRAMEM_128: 27_340.00,
    # M3 Mega
    GCPMachineType.M3_MEGAMEM_64: 10_252.00,
    GCPMachineType.M3_MEGAMEM_128: 20_504.00,
    # M2 Ultra (previous gen, larger memory)
    GCPMachineType.M2_ULTRAMEM_208: 42_686.00,
    GCPMachineType.M2_ULTRAMEM_416: 85_372.00,
    # C3 — SAP app servers
    GCPMachineType.C3_STANDARD_4: 152.00,
    GCPMachineType.C3_STANDARD_8: 304.00,
    GCPMachineType.C3_STANDARD_22: 836.00,
    GCPMachineType.C3_STANDARD_44: 1_672.00,
    GCPMachineType.C3_HIGHMEM_4: 202.00,
    GCPMachineType.C3_HIGHMEM_8: 404.00,
    GCPMachineType.C3_HIGHMEM_22: 1_111.00,
    # N2 — general purpose
    GCPMachineType.N2_STANDARD_8: 275.00,
    GCPMachineType.N2_STANDARD_16: 550.00,
    GCPMachineType.N2_STANDARD_32: 1_100.00,
    GCPMachineType.N2_HIGHMEM_16: 730.00,
    GCPMachineType.N2_HIGHMEM_32: 1_460.00,
    # Bare Metal
    GCPMachineType.BAREMETAL_BM_HANA: 120_000.00,
}

# HANA instance type to usable memory mapping (GB)
_MACHINE_MEMORY_GB: dict[GCPMachineType, int] = {
    GCPMachineType.M3_ULTRAMEM_32: 896,
    GCPMachineType.M3_ULTRAMEM_64: 1_792,
    GCPMachineType.M3_ULTRAMEM_128: 3_584,
    GCPMachineType.M3_MEGAMEM_64: 896,
    GCPMachineType.M3_MEGAMEM_128: 1_792,
    GCPMachineType.M2_ULTRAMEM_208: 5_888,
    GCPMachineType.M2_ULTRAMEM_416: 11_776,
    GCPMachineType.BAREMETAL_BM_HANA: 24_576,
}

# Regional price multiplier (relative to US_CENTRAL1 baseline)
_REGION_MULTIPLIER: dict[GCPRegion, float] = {
    GCPRegion.US_CENTRAL1: 1.00,
    GCPRegion.US_EAST1: 1.00,
    GCPRegion.US_EAST4: 1.05,
    GCPRegion.EUROPE_WEST1: 1.10,
    GCPRegion.EUROPE_WEST3: 1.15,
    GCPRegion.EUROPE_WEST4: 1.12,
    GCPRegion.ME_CENTRAL1: 1.25,
    GCPRegion.ME_CENTRAL2: 1.28,
    GCPRegion.ASIA_SOUTHEAST1: 1.08,
}

# Per-GB monthly storage prices (USD)
_PD_SSD_PER_GB_MONTHLY = 0.170
_PD_BALANCED_PER_GB_MONTHLY = 0.100
_FILESTORE_PER_GB_MONTHLY = 0.200
_GCS_NEARLINE_PER_GB_MONTHLY = 0.010

# Cloud Monitoring cost per SAP resource per month
_MONITORING_PER_RESOURCE_MONTHLY = 8.00

# Cloud NAT cost estimate per month
_CLOUD_NAT_MONTHLY = 45.00


class SAPSizingService:
    """Maps SAP Quick Sizer outputs to optimal GCP machine types and disk layouts."""

    # ------------------------------------------------------------------
    # HANA sizing
    # ------------------------------------------------------------------

    def recommend_hana_config(self, sizing: SizingInput) -> HANAConfig:
        """Select the smallest certified GCP instance that meets memory requirements."""
        instance_type = self._select_hana_instance(sizing.hana_memory_gb)
        memory_gb = _MACHINE_MEMORY_GB.get(instance_type, sizing.hana_memory_gb)

        data_disk_gb = max(256, int(sizing.db_size_gb * 1.5))
        log_disk_gb = max(512, int(sizing.db_size_gb * 0.5))
        shared_disk_gb = 1024
        backup_disk_gb = max(512, int(sizing.db_size_gb * 2.0))

        return HANAConfig(
            instance_type=instance_type,
            memory_gb=memory_gb,
            hana_data_disk_gb=data_disk_gb,
            hana_log_disk_gb=log_disk_gb,
            hana_shared_disk_gb=shared_disk_gb,
            backup_disk_gb=backup_disk_gb,
        )

    @staticmethod
    def _select_hana_instance(memory_gb: int) -> GCPMachineType:
        if memory_gb < 256:
            return GCPMachineType.M3_ULTRAMEM_32
        if memory_gb < 512:
            return GCPMachineType.M3_ULTRAMEM_32
        if memory_gb < 1024:
            return GCPMachineType.M3_ULTRAMEM_64
        if memory_gb < 2048:
            return GCPMachineType.M3_ULTRAMEM_128
        if memory_gb < 6000:
            return GCPMachineType.M2_ULTRAMEM_208
        if memory_gb < 12000:
            return GCPMachineType.M2_ULTRAMEM_416
        return GCPMachineType.BAREMETAL_BM_HANA

    # ------------------------------------------------------------------
    # App server sizing
    # ------------------------------------------------------------------

    def recommend_app_server_config(
        self,
        saps: int,
        users: int,
        landscape_type: SystemRole,
    ) -> AppServerConfig:
        """Select app server type and count based on SAPS rating and user count."""
        instance_type, base_count = self._select_app_instance(saps, users)

        if landscape_type == SystemRole.PRD:
            count = max(2, base_count)
            return AppServerConfig(
                instance_type=instance_type,
                instance_count=count,
                auto_scaling=True,
                min_instances=count,
                max_instances=count * 3,
            )

        if landscape_type == SystemRole.QAS:
            count = max(1, base_count)
            return AppServerConfig(
                instance_type=instance_type,
                instance_count=count,
                auto_scaling=True,
                min_instances=1,
                max_instances=count * 2,
            )

        # DEV — single instance, no auto-scaling
        return AppServerConfig(
            instance_type=instance_type,
            instance_count=1,
            auto_scaling=False,
            min_instances=1,
            max_instances=1,
        )

    @staticmethod
    def _select_app_instance(saps: int, users: int) -> tuple[GCPMachineType, int]:
        """Return (machine_type, instance_count) for application servers."""
        if saps < 5_000 and users < 200:
            return GCPMachineType.C3_STANDARD_4, 1
        if saps < 10_000 and users < 500:
            return GCPMachineType.C3_STANDARD_8, 1
        if saps < 30_000 and users < 1_500:
            return GCPMachineType.C3_STANDARD_22, 2
        if saps < 60_000 and users < 5_000:
            return GCPMachineType.C3_STANDARD_44, 2
        if saps < 100_000:
            return GCPMachineType.C3_HIGHMEM_22, 3
        return GCPMachineType.C3_HIGHMEM_22, 4

    # ------------------------------------------------------------------
    # Cost estimation
    # ------------------------------------------------------------------

    def calculate_cost_estimate(
        self,
        hana: HANAConfig,
        app: AppServerConfig,
        region: GCPRegion,
        ha_enabled: bool,
        dr_enabled: bool,
    ) -> CostEstimate:
        """Calculate monthly GCP spend with regional pricing and CUD discounts."""
        multiplier = _REGION_MULTIPLIER.get(region, 1.0)

        # HANA compute — double if HA (active/passive)
        hana_base = _MACHINE_MONTHLY_COST.get(hana.instance_type, 0.0)
        hana_instances = 2 if ha_enabled else 1
        hana_monthly = hana_base * hana_instances * multiplier

        # DR adds another HANA instance in a different region
        if dr_enabled:
            hana_monthly += hana_base * multiplier

        # App server compute
        app_base = _MACHINE_MONTHLY_COST.get(app.instance_type, 0.0)
        app_monthly = app_base * app.instance_count * multiplier

        # Storage: PD-SSD for log, Balanced PD for data/shared, Filestore for transport
        log_storage = hana.hana_log_disk_gb * _PD_SSD_PER_GB_MONTHLY
        data_storage = hana.hana_data_disk_gb * _PD_BALANCED_PER_GB_MONTHLY
        shared_storage = hana.hana_shared_disk_gb * _PD_BALANCED_PER_GB_MONTHLY
        filestore_transport = 1024 * _FILESTORE_PER_GB_MONTHLY  # 1TB transport dir
        storage_monthly = (log_storage + data_storage + shared_storage + filestore_transport) * multiplier

        # HA doubles disk costs for the standby node
        if ha_enabled:
            storage_monthly += (log_storage + data_storage + shared_storage) * multiplier

        # Network: Cloud NAT + bandwidth estimate
        network_monthly = _CLOUD_NAT_MONTHLY * multiplier
        # Egress estimate: ~2TB/month at $0.085/GB
        network_monthly += 2048 * 0.085

        # Backup: GCS Nearline for Backint
        backup_monthly = hana.backup_disk_gb * _GCS_NEARLINE_PER_GB_MONTHLY * multiplier

        # Monitoring: per-resource pricing (HANA + app instances + network)
        resource_count = hana_instances + app.instance_count + 3  # +3 for network/storage/backup
        monitoring_monthly = resource_count * _MONITORING_PER_RESOURCE_MONTHLY * multiplier

        # CUD: 3-year committed use discount for HANA, 1-year for app servers
        cud_percentage = 37.0 if hana_monthly > 20_000 else 20.0

        return CostEstimate(
            hana_monthly=round(hana_monthly, 2),
            app_server_monthly=round(app_monthly, 2),
            storage_monthly=round(storage_monthly, 2),
            network_monthly=round(network_monthly, 2),
            backup_monthly=round(backup_monthly, 2),
            monitoring_monthly=round(monitoring_monthly, 2),
            cud_discount_percentage=cud_percentage,
        )
