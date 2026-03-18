"""GCP infrastructure value objects — immutable types for SAP on GCP sizing and provisioning.

Architectural Intent:
- Canonical GCP machine types, regions, and SAP-specific configurations
- All value objects are frozen dataclasses or enums — no mutable state
- Cost estimation uses approximate on-demand GCP pricing (2026 rates)
- Sizing inputs map directly from SAP Quick Sizer output format
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.value_objects.object_type import SystemRole

# ---------------------------------------------------------------------------
# GCP Region — key SAP-certified regions
# ---------------------------------------------------------------------------


class GCPRegion(Enum):
    US_CENTRAL1 = "us-central1"
    US_EAST1 = "us-east1"
    US_EAST4 = "us-east4"
    EUROPE_WEST1 = "europe-west1"
    EUROPE_WEST3 = "europe-west3"
    EUROPE_WEST4 = "europe-west4"
    ME_CENTRAL1 = "me-central1"
    ME_CENTRAL2 = "me-central2"
    ASIA_SOUTHEAST1 = "asia-southeast1"


# ---------------------------------------------------------------------------
# GCP Machine Types — SAP-certified HANA and app server instances
# ---------------------------------------------------------------------------


class GCPMachineType(Enum):
    # M3 Ultra — memory-optimised for HANA (up to 30.5 TB)
    M3_ULTRAMEM_32 = "m3-ultramem-32"
    M3_ULTRAMEM_64 = "m3-ultramem-64"
    M3_ULTRAMEM_128 = "m3-ultramem-128"

    # M3 Mega — large memory for HANA
    M3_MEGAMEM_64 = "m3-megamem-64"
    M3_MEGAMEM_128 = "m3-megamem-128"

    # M2 Ultra — previous gen, still certified for HANA
    M2_ULTRAMEM_208 = "m2-ultramem-208"
    M2_ULTRAMEM_416 = "m2-ultramem-416"

    # C3 — compute-optimised for SAP application servers
    C3_STANDARD_4 = "c3-standard-4"
    C3_STANDARD_8 = "c3-standard-8"
    C3_STANDARD_22 = "c3-standard-22"
    C3_STANDARD_44 = "c3-standard-44"
    C3_HIGHMEM_4 = "c3-highmem-4"
    C3_HIGHMEM_8 = "c3-highmem-8"
    C3_HIGHMEM_22 = "c3-highmem-22"

    # N2 — general-purpose for lighter workloads
    N2_STANDARD_8 = "n2-standard-8"
    N2_STANDARD_16 = "n2-standard-16"
    N2_STANDARD_32 = "n2-standard-32"
    N2_HIGHMEM_16 = "n2-highmem-16"
    N2_HIGHMEM_32 = "n2-highmem-32"

    # Bare Metal Solution for very large HANA (>16 TB)
    BAREMETAL_BM_HANA = "bms-hana"


# ---------------------------------------------------------------------------
# HANA Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HANAConfig:
    """HANA database instance sizing — disk sizes in GB."""

    instance_type: GCPMachineType
    memory_gb: int
    hana_data_disk_gb: int
    hana_log_disk_gb: int
    hana_shared_disk_gb: int
    backup_disk_gb: int


# ---------------------------------------------------------------------------
# App Server Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppServerConfig:
    """SAP application server sizing with optional auto-scaling."""

    instance_type: GCPMachineType
    instance_count: int
    auto_scaling: bool
    min_instances: int
    max_instances: int


# ---------------------------------------------------------------------------
# Network Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NetworkConfig:
    """Shared VPC network layout for SAP landing zone."""

    vpc_name: str
    subnet_cidr_db: str
    subnet_cidr_app: str
    subnet_cidr_web: str
    enable_cloud_nat: bool
    enable_private_google_access: bool
    interconnect_bandwidth_gbps: float | None


# ---------------------------------------------------------------------------
# Security Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecurityConfig:
    """Security controls for SAP landing zone."""

    enable_cmek: bool
    enable_vpc_sc: bool
    enable_os_login: bool
    enable_binary_auth: bool
    kms_key_ring: str | None


# ---------------------------------------------------------------------------
# Cost Estimate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CostEstimate:
    """Monthly and annual GCP cost breakdown with CUD optimisation."""

    hana_monthly: float
    app_server_monthly: float
    storage_monthly: float
    network_monthly: float
    backup_monthly: float
    monitoring_monthly: float
    cud_discount_percentage: float

    @property
    def total_monthly(self) -> float:
        return (
            self.hana_monthly
            + self.app_server_monthly
            + self.storage_monthly
            + self.network_monthly
            + self.backup_monthly
            + self.monitoring_monthly
        )

    @property
    def total_annual(self) -> float:
        return self.total_monthly * 12.0

    @property
    def cud_monthly(self) -> float:
        return self.total_monthly * (1.0 - self.cud_discount_percentage / 100.0)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationStatus(Enum):
    NOT_VALIDATED = "NOT_VALIDATED"
    VALIDATING = "VALIDATING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNINGS = "WARNINGS"


@dataclass(frozen=True)
class ValidationResult:
    """Result of SAP certification validation checks."""

    status: ValidationStatus
    checks_passed: int
    checks_failed: int
    warnings: tuple[str, ...]
    errors: tuple[str, ...]


# ---------------------------------------------------------------------------
# Sizing Input — from SAP Quick Sizer or manual entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SizingInput:
    """Sizing parameters from SAP Quick Sizer XML or manual input."""

    saps_rating: int
    hana_memory_gb: int
    db_size_gb: float
    concurrent_users: int
    landscape_type: SystemRole
