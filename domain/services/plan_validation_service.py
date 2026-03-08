"""Plan validation service — checks SAP on GCP certification requirements.

Architectural Intent:
- Pure domain logic validating infrastructure plans against SAP certification rules
- No infrastructure dependencies — operates entirely on domain value objects
- Produces immutable ValidationResult with pass/fail/warning categorisation
- Each check is independent and could run in parallel
"""

from __future__ import annotations

import ipaddress

from domain.entities.infrastructure_plan import InfrastructurePlan
from domain.value_objects.gcp_types import (
    GCPMachineType,
    ValidationResult,
    ValidationStatus,
)


# Minimum HANA memory (GB) per certified instance type
_MIN_HANA_MEMORY: dict[GCPMachineType, int] = {
    GCPMachineType.M3_ULTRAMEM_32: 256,
    GCPMachineType.M3_ULTRAMEM_64: 512,
    GCPMachineType.M3_ULTRAMEM_128: 1024,
    GCPMachineType.M3_MEGAMEM_64: 512,
    GCPMachineType.M3_MEGAMEM_128: 1024,
    GCPMachineType.M2_ULTRAMEM_208: 2048,
    GCPMachineType.M2_ULTRAMEM_416: 4096,
    GCPMachineType.BAREMETAL_BM_HANA: 6144,
}

# SAP-certified HANA instance types
_CERTIFIED_HANA_TYPES: frozenset[GCPMachineType] = frozenset({
    GCPMachineType.M3_ULTRAMEM_32,
    GCPMachineType.M3_ULTRAMEM_64,
    GCPMachineType.M3_ULTRAMEM_128,
    GCPMachineType.M3_MEGAMEM_64,
    GCPMachineType.M3_MEGAMEM_128,
    GCPMachineType.M2_ULTRAMEM_208,
    GCPMachineType.M2_ULTRAMEM_416,
    GCPMachineType.BAREMETAL_BM_HANA,
})

# Minimum disk sizes per SAP Note 1944799
_MIN_LOG_DISK_GB = 512
_MIN_DATA_DISK_GB = 256
_MIN_SHARED_DISK_GB = 512
_MIN_BACKUP_DISK_GB = 256


class PlanValidationService:
    """Validates an InfrastructurePlan against SAP on GCP certification requirements."""

    def validate_sap_certification(
        self, plan: InfrastructurePlan
    ) -> ValidationResult:
        """Run all certification checks and return an aggregate result."""
        errors: list[str] = []
        warnings: list[str] = []
        checks_passed = 0
        checks_failed = 0

        # ------------------------------------------------------------------
        # Check 1: HANA instance type is SAP-certified
        # ------------------------------------------------------------------
        if plan.hana_config.instance_type in _CERTIFIED_HANA_TYPES:
            checks_passed += 1
        else:
            checks_failed += 1
            errors.append(
                f"HANA instance type {plan.hana_config.instance_type.value} "
                f"is not SAP-certified for HANA workloads."
            )

        # ------------------------------------------------------------------
        # Check 2: HANA memory meets minimum for selected instance type
        # ------------------------------------------------------------------
        min_memory = _MIN_HANA_MEMORY.get(plan.hana_config.instance_type, 0)
        if plan.hana_config.memory_gb >= min_memory:
            checks_passed += 1
        else:
            checks_failed += 1
            errors.append(
                f"HANA memory {plan.hana_config.memory_gb} GB is below the "
                f"minimum {min_memory} GB for {plan.hana_config.instance_type.value}."
            )

        # ------------------------------------------------------------------
        # Check 3: HA must be enabled for production landscapes
        # ------------------------------------------------------------------
        # We infer production from the plan context — if DR is enabled, it is
        # likely PRD. Check HA explicitly.
        if plan.ha_enabled:
            checks_passed += 1
        else:
            warnings.append(
                "High availability is not enabled. "
                "HA is mandatory for SAP production landscapes (PRD)."
            )

        # ------------------------------------------------------------------
        # Check 4: DR recommended for production
        # ------------------------------------------------------------------
        if plan.dr_enabled or plan.dr_region is not None:
            checks_passed += 1
        else:
            warnings.append(
                "Disaster recovery is not configured. "
                "Cross-region DR is recommended for production SAP landscapes."
            )

        # ------------------------------------------------------------------
        # Check 5: Disk sizes meet SAP minimums
        # ------------------------------------------------------------------
        disk_ok = True
        if plan.hana_config.hana_log_disk_gb < _MIN_LOG_DISK_GB:
            checks_failed += 1
            disk_ok = False
            errors.append(
                f"HANA log disk {plan.hana_config.hana_log_disk_gb} GB is below "
                f"the minimum {_MIN_LOG_DISK_GB} GB."
            )
        if plan.hana_config.hana_data_disk_gb < _MIN_DATA_DISK_GB:
            checks_failed += 1
            disk_ok = False
            errors.append(
                f"HANA data disk {plan.hana_config.hana_data_disk_gb} GB is below "
                f"the minimum {_MIN_DATA_DISK_GB} GB."
            )
        if plan.hana_config.hana_shared_disk_gb < _MIN_SHARED_DISK_GB:
            checks_failed += 1
            disk_ok = False
            errors.append(
                f"HANA shared disk {plan.hana_config.hana_shared_disk_gb} GB is below "
                f"the minimum {_MIN_SHARED_DISK_GB} GB."
            )
        if plan.hana_config.backup_disk_gb < _MIN_BACKUP_DISK_GB:
            checks_failed += 1
            disk_ok = False
            errors.append(
                f"HANA backup disk {plan.hana_config.backup_disk_gb} GB is below "
                f"the minimum {_MIN_BACKUP_DISK_GB} GB."
            )
        if disk_ok:
            checks_passed += 1

        # ------------------------------------------------------------------
        # Check 6: Network subnets do not overlap
        # ------------------------------------------------------------------
        try:
            db_net = ipaddress.ip_network(plan.network_config.subnet_cidr_db, strict=False)
            app_net = ipaddress.ip_network(plan.network_config.subnet_cidr_app, strict=False)
            web_net = ipaddress.ip_network(plan.network_config.subnet_cidr_web, strict=False)
            overlap = (
                db_net.overlaps(app_net)
                or db_net.overlaps(web_net)
                or app_net.overlaps(web_net)
            )
            if overlap:
                checks_failed += 1
                errors.append(
                    "Subnet CIDRs overlap. Each SAP tier (DB, App, Web) must use "
                    "non-overlapping subnets."
                )
            else:
                checks_passed += 1
        except ValueError as exc:
            checks_failed += 1
            errors.append(f"Invalid CIDR notation in network config: {exc}")

        # ------------------------------------------------------------------
        # Check 7: CMEK recommended for production
        # ------------------------------------------------------------------
        if plan.security_config.enable_cmek:
            checks_passed += 1
        else:
            warnings.append(
                "Customer-managed encryption keys (CMEK) are not enabled. "
                "CMEK via Cloud KMS is recommended for production SAP workloads."
            )

        # ------------------------------------------------------------------
        # Check 8: OS Login recommended
        # ------------------------------------------------------------------
        if plan.security_config.enable_os_login:
            checks_passed += 1
        else:
            warnings.append(
                "OS Login is not enabled. OS Login with 2FA is recommended "
                "for SAP compute instances."
            )

        # ------------------------------------------------------------------
        # Aggregate result
        # ------------------------------------------------------------------
        if checks_failed > 0:
            status = ValidationStatus.FAILED
        elif warnings:
            status = ValidationStatus.WARNINGS
        else:
            status = ValidationStatus.PASSED

        return ValidationResult(
            status=status,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )
