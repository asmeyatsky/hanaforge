"""StubMigrationExecutor — simulates SAP migration task execution for development.

Implements MigrationExecutorPort with configurable delays and success rates,
returning realistic result dicts for each task type.
"""

from __future__ import annotations

import asyncio
import random

from domain.entities.migration_task import MigrationTask
from domain.value_objects.migration_types import MigrationTaskType

# ------------------------------------------------------------------
# Simulated durations (seconds in stub mode) and success rates
# ------------------------------------------------------------------
_TASK_PROFILES: dict[MigrationTaskType, dict] = {
    MigrationTaskType.DMO_PRECHECK: {
        "delay_seconds": 0.1,
        "duration_minutes": 45,
        "success_rate": 0.95,
        "result_template": {
            "checks_passed": 42,
            "checks_failed": 0,
            "warnings": 3,
            "abap_compatibility": "PASS",
            "db_consistency": "PASS",
            "disk_space_sufficient": True,
        },
    },
    MigrationTaskType.DMO_HANA_UPGRADE: {
        "delay_seconds": 0.2,
        "duration_minutes": 360,
        "success_rate": 0.90,
        "result_template": {
            "source_db": "Oracle",
            "target_db": "HANA",
            "tables_migrated": 15420,
            "data_volume_gb": 850,
            "index_rebuild_status": "COMPLETE",
        },
    },
    MigrationTaskType.DMO_SUM_EXECUTION: {
        "delay_seconds": 0.3,
        "duration_minutes": 480,
        "success_rate": 0.85,
        "result_template": {
            "phases_completed": ["DETECT", "PREPROCESS", "SHADOW_IMPORT", "EXECUTION"],
            "spdd_adjustments": 12,
            "spau_adjustments": 28,
            "simplification_items_resolved": 156,
            "tables_converted": ["BSEG", "ACDOCA", "MATDOC", "EKPO"],
        },
    },
    MigrationTaskType.DMO_POSTCHECK: {
        "delay_seconds": 0.1,
        "duration_minutes": 30,
        "success_rate": 0.98,
        "result_template": {
            "data_integrity": "PASS",
            "acdoca_migration": "COMPLETE",
            "material_ledger": "ACTIVATED",
            "business_partner_status": "MIGRATED",
        },
    },
    MigrationTaskType.SDT_SHELL_CREATION: {
        "delay_seconds": 0.2,
        "duration_minutes": 120,
        "success_rate": 0.92,
        "result_template": {
            "system_id": "S4H",
            "client": "100",
            "org_structure_created": True,
            "master_data_framework": "INITIALIZED",
        },
    },
    MigrationTaskType.SDT_DATA_LOAD: {
        "delay_seconds": 0.2,
        "duration_minutes": 240,
        "success_rate": 0.88,
        "result_template": {
            "records_loaded": 1250000,
            "tables_affected": 324,
            "delta_capable": True,
            "load_mode": "INITIAL",
        },
    },
    MigrationTaskType.SDT_RECONCILIATION: {
        "delay_seconds": 0.1,
        "duration_minutes": 90,
        "success_rate": 0.95,
        "result_template": {
            "record_count_match": True,
            "financial_balance_match": True,
            "material_stock_match": True,
            "discrepancies": 0,
            "tolerance_pct": 0.01,
        },
    },
    MigrationTaskType.PCA_CLIENT_DELETION: {
        "delay_seconds": 0.1,
        "duration_minutes": 30,
        "success_rate": 0.99,
        "result_template": {
            "clients_deleted": ["066", "090"],
            "space_freed_gb": 12.5,
        },
    },
    MigrationTaskType.PCA_CLIENT_COPY: {
        "delay_seconds": 0.2,
        "duration_minutes": 180,
        "success_rate": 0.93,
        "result_template": {
            "source_client": "000",
            "target_client": "100",
            "copy_profile": "SAP_CUST",
            "objects_copied": 45230,
        },
    },
    MigrationTaskType.PCA_TRANSPORT_IMPORT: {
        "delay_seconds": 0.2,
        "duration_minutes": 120,
        "success_rate": 0.90,
        "result_template": {
            "transports_imported": 156,
            "max_return_code": 4,
            "customising_transports": 48,
            "workbench_transports": 108,
        },
    },
    MigrationTaskType.PCA_USER_MASTER_IMPORT: {
        "delay_seconds": 0.1,
        "duration_minutes": 60,
        "success_rate": 0.97,
        "result_template": {
            "users_imported": 2340,
            "roles_assigned": 8920,
            "sap_all_removed": True,
            "sap_new_removed": True,
        },
    },
    MigrationTaskType.MANUAL_CHECKPOINT: {
        "delay_seconds": 0.05,
        "duration_minutes": 15,
        "success_rate": 1.0,
        "result_template": {
            "approval_status": "AUTO_APPROVED",
            "approvers": ["tech_lead", "func_lead", "pm"],
        },
    },
    MigrationTaskType.SYSTEM_HEALTH_CHECK: {
        "delay_seconds": 0.1,
        "duration_minutes": 20,
        "success_rate": 0.97,
        "result_template": {
            "sm51_services": "ALL_RUNNING",
            "sm66_work_processes": "AVAILABLE",
            "sm37_batch_jobs": "NORMAL",
            "sm59_rfc_destinations": "ALL_ACTIVE",
        },
    },
    MigrationTaskType.DATA_VALIDATION: {
        "delay_seconds": 0.1,
        "duration_minutes": 60,
        "success_rate": 0.95,
        "result_template": {
            "config_consistency": "PASS",
            "master_data_integrity": "PASS",
            "system_parameters": "PASS",
            "validation_rules_checked": 248,
        },
    },
    MigrationTaskType.CUSTOM: {
        "delay_seconds": 0.1,
        "duration_minutes": 60,
        "success_rate": 0.90,
        "result_template": {"status": "COMPLETED"},
    },
}


class StubMigrationExecutor:
    """Simulates migration task execution — implements MigrationExecutorPort.

    For development and testing. Configurable failure injection.
    """

    def __init__(
        self,
        *,
        force_failure: bool = False,
        force_success: bool = False,
        delay_multiplier: float = 1.0,
    ) -> None:
        self._force_failure = force_failure
        self._force_success = force_success
        self._delay_multiplier = delay_multiplier

    async def execute_task(self, task: MigrationTask) -> dict:
        """Simulate task execution and return a result dict."""
        profile = _TASK_PROFILES.get(
            task.task_type,
            _TASK_PROFILES[MigrationTaskType.CUSTOM],
        )

        # Simulate execution delay
        delay = profile["delay_seconds"] * self._delay_multiplier
        await asyncio.sleep(delay)

        # Determine success or failure
        if self._force_failure:
            raise RuntimeError(f"Simulated failure for task '{task.task_name}' ({task.task_type.value})")

        if not self._force_success:
            if random.random() > profile["success_rate"]:
                raise RuntimeError(
                    f"Simulated random failure for task '{task.task_name}' (success_rate={profile['success_rate']})"
                )

        # Build result
        result = dict(profile["result_template"])
        result["duration_minutes"] = profile["duration_minutes"]
        result["metrics"] = {
            "error_count": random.randint(0, 2),
            "elapsed_minutes": profile["duration_minutes"],
            "last_progress_minutes": random.randint(0, 5),
            "disk_usage_pct": random.uniform(40.0, 75.0),
            "memory_usage_pct": random.uniform(50.0, 80.0),
        }

        return result

    async def check_system_health(self, connection_params: dict) -> dict:
        """Simulate a system health check."""
        await asyncio.sleep(0.05 * self._delay_multiplier)
        return {
            "status": "HEALTHY",
            "sm51_services": "ALL_RUNNING",
            "sm66_work_processes": "AVAILABLE",
            "sm37_batch_jobs": "NORMAL",
            "sm59_rfc_destinations": "ALL_ACTIVE",
            "db_status": "ONLINE",
            "memory_usage_pct": random.uniform(50.0, 80.0),
            "disk_usage_pct": random.uniform(40.0, 70.0),
        }
