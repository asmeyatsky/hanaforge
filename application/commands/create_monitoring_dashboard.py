"""CreateMonitoringDashboardUseCase — provisions Cloud Monitoring dashboards and alerts.

Creates SAP-specific and GCP infrastructure monitoring dashboards with
appropriate alert policies for an SAP S/4HANA migration programme.
"""

from __future__ import annotations

import logging

from domain.ports.infrastructure_ports import (
    CloudMonitoringPort,
    InfrastructurePlanRepositoryPort,
    MonitoringDashboardConfig,
)

logger = logging.getLogger(__name__)


class CreateMonitoringDashboardUseCase:
    """Single-responsibility use case: create Cloud Monitoring dashboards and alert policies."""

    def __init__(
        self,
        plan_repo: InfrastructurePlanRepositoryPort,
        monitoring: CloudMonitoringPort,
    ) -> None:
        self._plan_repo = plan_repo
        self._monitoring = monitoring

    async def execute(
        self,
        programme_id: str,
        custom_thresholds: dict[str, float] | None = None,
    ) -> dict:
        """Create monitoring dashboards and alert policies for a programme.

        Steps:
        1. Load the infrastructure plan to discover provisioned resources.
        2. Create an SAP/HANA-focused monitoring dashboard.
        3. Create a GCP infrastructure monitoring dashboard.
        4. Create alert policies for critical SAP and GCP metrics.
        5. Return the combined dashboard configs and console URLs.
        """
        # 1. Load infrastructure plan
        plan = await self._plan_repo.get_latest_by_programme(programme_id)
        plan_ref = plan.id if plan else f"pending-{programme_id}"

        logger.info(
            "Creating monitoring dashboards for programme %s (plan_ref=%s)",
            programme_id,
            plan_ref,
        )

        # 2. SAP monitoring dashboard
        sap_metrics = self._monitoring.build_sap_metrics()
        sap_thresholds = self._monitoring.default_sap_thresholds()
        if custom_thresholds:
            sap_thresholds.update(custom_thresholds)

        sap_config = MonitoringDashboardConfig(
            name=f"HanaForge SAP Monitoring — {programme_id}",
            metrics=sap_metrics,
            alert_thresholds=sap_thresholds,
        )
        sap_dashboard = await self._monitoring.create_dashboard(sap_config)

        # 3. GCP infrastructure monitoring dashboard
        gcp_metrics = self._monitoring.build_gcp_metrics()
        gcp_config = MonitoringDashboardConfig(
            name=f"HanaForge GCP Infrastructure — {programme_id}",
            metrics=gcp_metrics,
            alert_thresholds={
                k: v
                for k, v in sap_thresholds.items()
                if k in {"cpu_utilization", "memory_utilization", "disk_utilization"}
            },
        )
        gcp_dashboard = await self._monitoring.create_dashboard(gcp_config)

        # 4. Create alert policies for all thresholds
        alert_policies = await self._monitoring.create_alert_policies(
            plan_ref=plan_ref,
            thresholds=sap_thresholds,
        )

        # 5. Build console URLs
        sap_dashboard_id = sap_dashboard["dashboardId"]
        gcp_dashboard_id = gcp_dashboard["dashboardId"]

        sap_url = await self._monitoring.get_dashboard_url(sap_dashboard_id)
        gcp_url = await self._monitoring.get_dashboard_url(gcp_dashboard_id)

        return {
            "programme_id": programme_id,
            "plan_ref": plan_ref,
            "sap_dashboard": sap_dashboard,
            "gcp_dashboard": gcp_dashboard,
            "sap_dashboard_url": sap_url,
            "gcp_dashboard_url": gcp_url,
            "alert_policies": alert_policies,
            "alert_policy_count": len(alert_policies),
            "thresholds_applied": sap_thresholds,
        }

    async def get_status(self, programme_id: str) -> dict:
        """Return the current monitoring dashboard status for a programme.

        This is a lightweight check that returns configuration metadata
        without re-creating the dashboards.
        """
        plan = await self._plan_repo.get_latest_by_programme(programme_id)
        plan_ref = plan.id if plan else None
        has_plan = plan is not None

        default_thresholds = self._monitoring.default_sap_thresholds()

        return {
            "programme_id": programme_id,
            "plan_ref": plan_ref,
            "infrastructure_plan_exists": has_plan,
            "sap_metrics_count": len(self._monitoring.build_sap_metrics()),
            "gcp_metrics_count": len(self._monitoring.build_gcp_metrics()),
            "default_thresholds": default_thresholds,
            "status": "configured" if has_plan else "pending_infrastructure",
        }
