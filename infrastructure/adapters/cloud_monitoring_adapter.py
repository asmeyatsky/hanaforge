"""CloudMonitoringAdapter — generates Google Cloud Monitoring dashboard configs and alert policies.

Implements CloudMonitoringPort with fully-structured JSON configs matching the
Google Cloud Monitoring API format.  Actual API calls are stubbed for now; the
structured payloads are ready for direct submission to the Monitoring v3 API.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from domain.ports.infrastructure_ports import MonitoringDashboardConfig

logger = logging.getLogger(__name__)


class CloudMonitoringAdapter:
    """Generates Cloud Monitoring dashboard JSON and alert policy configs.

    Covers both SAP-specific metrics (HANA memory, dialog response time, etc.)
    and GCP infrastructure metrics (CPU, memory, disk, network).
    """

    def __init__(self, gcp_project_id: str = "") -> None:
        self._project_id = gcp_project_id

    # ------------------------------------------------------------------
    # CloudMonitoringPort implementation
    # ------------------------------------------------------------------

    async def create_dashboard(self, config: MonitoringDashboardConfig) -> dict:
        """Build a Cloud Monitoring dashboard JSON payload from *config*.

        Returns a dict matching the ``google.monitoring.dashboard.v1.Dashboard``
        schema, ready for ``dashboards.create`` API submission.
        """
        dashboard_id = str(uuid.uuid4())
        logger.info(
            "CloudMonitoringAdapter: creating dashboard %r (id=%s)",
            config.name,
            dashboard_id,
        )

        tiles = [self._metric_to_tile(m) for m in config.metrics]

        dashboard_payload: dict = {
            "name": f"projects/{self._project_id}/dashboards/{dashboard_id}",
            "displayName": config.name,
            "dashboardId": dashboard_id,
            "mosaicLayout": {
                "columns": 12,
                "tiles": tiles,
            },
            "labels": {
                "hanaforge-managed": "",
                "created-by": "hanaforge-monitoring-adapter",
            },
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        return dashboard_payload

    async def create_alert_policies(
        self, plan_ref: str, thresholds: dict[str, float]
    ) -> list[dict]:
        """Generate Cloud Monitoring alert policy payloads for the given thresholds.

        Each threshold key maps to a metric type and generates a separate
        ``AlertPolicy`` JSON object.
        """
        logger.info(
            "CloudMonitoringAdapter: creating %d alert policies for plan %s",
            len(thresholds),
            plan_ref,
        )

        metric_type_map = self._threshold_to_metric_type_map()
        policies: list[dict] = []

        for metric_key, threshold_value in thresholds.items():
            metric_type = metric_type_map.get(
                metric_key, f"custom.googleapis.com/sap/{metric_key}"
            )
            policy_id = str(uuid.uuid4())

            policy: dict = {
                "name": f"projects/{self._project_id}/alertPolicies/{policy_id}",
                "displayName": f"HanaForge — {metric_key.replace('_', ' ').title()} Alert",
                "documentation": {
                    "content": (
                        f"Alert triggered when {metric_key} exceeds "
                        f"threshold of {threshold_value} for plan {plan_ref}."
                    ),
                    "mimeType": "text/markdown",
                },
                "userLabels": {
                    "hanaforge-plan-ref": plan_ref,
                    "hanaforge-managed": "true",
                },
                "conditions": [
                    {
                        "displayName": f"{metric_key} > {threshold_value}",
                        "conditionThreshold": {
                            "filter": (
                                f'metric.type="{metric_type}" '
                                f'AND resource.type="gce_instance"'
                            ),
                            "comparison": "COMPARISON_GT",
                            "thresholdValue": threshold_value,
                            "duration": "300s",
                            "aggregations": [
                                {
                                    "alignmentPeriod": "60s",
                                    "perSeriesAligner": "ALIGN_MEAN",
                                }
                            ],
                            "trigger": {"count": 1},
                        },
                    }
                ],
                "combiner": "OR",
                "enabled": True,
                "notificationChannels": [],
                "severity": self._severity_for_metric(metric_key),
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            policies.append(policy)

        return policies

    async def get_dashboard_url(self, dashboard_id: str) -> str:
        """Return the Cloud Console URL for a monitoring dashboard."""
        return (
            f"https://console.cloud.google.com/monitoring/dashboards/custom/"
            f"{dashboard_id}?project={self._project_id}"
        )

    # ------------------------------------------------------------------
    # SAP-specific dashboard builders
    # ------------------------------------------------------------------

    def build_sap_metrics(self) -> list[dict[str, object]]:
        """Return the standard SAP/HANA metric definitions for a dashboard."""
        return [
            {
                "metric_type": "custom.googleapis.com/sap/hana/memory_utilization",
                "display_name": "HANA Memory Utilization",
                "unit": "%",
                "description": "SAP HANA resident memory as a percentage of allocatable memory",
                "category": "sap_hana",
            },
            {
                "metric_type": "custom.googleapis.com/sap/dialog_response_time",
                "display_name": "Dialog Response Time",
                "unit": "ms",
                "description": "Average SAP dialog step response time",
                "category": "sap_performance",
            },
            {
                "metric_type": "custom.googleapis.com/sap/batch_throughput",
                "display_name": "Batch Job Throughput",
                "unit": "jobs/min",
                "description": "Number of batch jobs completed per minute",
                "category": "sap_performance",
            },
            {
                "metric_type": "custom.googleapis.com/sap/rfc_response_time",
                "display_name": "RFC Response Time",
                "unit": "ms",
                "description": "Average RFC call response time",
                "category": "sap_performance",
            },
            {
                "metric_type": "custom.googleapis.com/sap/enqueue_time",
                "display_name": "Enqueue Lock Time",
                "unit": "ms",
                "description": "Average SAP enqueue lock wait time",
                "category": "sap_performance",
            },
            {
                "metric_type": "custom.googleapis.com/sap/hana/disk_usage",
                "display_name": "HANA Data Volume Usage",
                "unit": "%",
                "description": "HANA data volume disk utilization percentage",
                "category": "sap_hana",
            },
            {
                "metric_type": "custom.googleapis.com/sap/hana/backup_age",
                "display_name": "HANA Last Backup Age",
                "unit": "hours",
                "description": "Hours since last successful HANA backup",
                "category": "sap_hana",
            },
        ]

    def build_gcp_metrics(self) -> list[dict[str, object]]:
        """Return the standard GCP infrastructure metric definitions."""
        return [
            {
                "metric_type": "compute.googleapis.com/instance/cpu/utilization",
                "display_name": "CPU Utilization",
                "unit": "%",
                "description": "GCE instance CPU utilization",
                "category": "gcp_compute",
            },
            {
                "metric_type": "compute.googleapis.com/instance/memory/balloon/ram_used",
                "display_name": "Memory Utilization",
                "unit": "bytes",
                "description": "GCE instance memory usage",
                "category": "gcp_compute",
            },
            {
                "metric_type": "compute.googleapis.com/instance/disk/read_bytes_count",
                "display_name": "Disk Read Throughput",
                "unit": "bytes/s",
                "description": "Disk read bytes per second",
                "category": "gcp_storage",
            },
            {
                "metric_type": "compute.googleapis.com/instance/disk/write_bytes_count",
                "display_name": "Disk Write Throughput",
                "unit": "bytes/s",
                "description": "Disk write bytes per second",
                "category": "gcp_storage",
            },
            {
                "metric_type": "compute.googleapis.com/instance/network/received_bytes_count",
                "display_name": "Network Ingress",
                "unit": "bytes/s",
                "description": "Network bytes received per second",
                "category": "gcp_network",
            },
            {
                "metric_type": "compute.googleapis.com/instance/network/sent_bytes_count",
                "display_name": "Network Egress",
                "unit": "bytes/s",
                "description": "Network bytes sent per second",
                "category": "gcp_network",
            },
            {
                "metric_type": "compute.googleapis.com/instance/disk/percent_used",
                "display_name": "Disk Utilization",
                "unit": "%",
                "description": "Persistent disk utilization percentage",
                "category": "gcp_storage",
            },
        ]

    def default_sap_thresholds(self) -> dict[str, float]:
        """Return sensible default alert thresholds for SAP/HANA workloads."""
        return {
            "hana_memory_utilization": 85.0,
            "dialog_response_time": 1000.0,
            "batch_throughput_low": 50.0,
            "rfc_response_time": 500.0,
            "enqueue_time": 50.0,
            "hana_disk_usage": 90.0,
            "hana_backup_age": 24.0,
            "cpu_utilization": 90.0,
            "memory_utilization": 90.0,
            "disk_utilization": 85.0,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _metric_to_tile(metric: dict[str, object]) -> dict:
        """Convert a metric definition dict to a Cloud Monitoring mosaic tile."""
        return {
            "width": 6,
            "height": 4,
            "widget": {
                "title": str(metric.get("display_name", "Metric")),
                "xyChart": {
                    "dataSets": [
                        {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": (
                                        f'metric.type="{metric["metric_type"]}"'
                                    ),
                                    "aggregation": {
                                        "alignmentPeriod": "60s",
                                        "perSeriesAligner": "ALIGN_MEAN",
                                    },
                                },
                            },
                            "plotType": "LINE",
                        }
                    ],
                    "timeshiftDuration": "0s",
                    "yAxis": {
                        "label": str(metric.get("unit", "")),
                        "scale": "LINEAR",
                    },
                },
            },
        }

    @staticmethod
    def _threshold_to_metric_type_map() -> dict[str, str]:
        """Map threshold keys to their Cloud Monitoring metric type strings."""
        return {
            "hana_memory_utilization": "custom.googleapis.com/sap/hana/memory_utilization",
            "dialog_response_time": "custom.googleapis.com/sap/dialog_response_time",
            "batch_throughput_low": "custom.googleapis.com/sap/batch_throughput",
            "rfc_response_time": "custom.googleapis.com/sap/rfc_response_time",
            "enqueue_time": "custom.googleapis.com/sap/enqueue_time",
            "hana_disk_usage": "custom.googleapis.com/sap/hana/disk_usage",
            "hana_backup_age": "custom.googleapis.com/sap/hana/backup_age",
            "cpu_utilization": "compute.googleapis.com/instance/cpu/utilization",
            "memory_utilization": "compute.googleapis.com/instance/memory/balloon/ram_used",
            "disk_utilization": "compute.googleapis.com/instance/disk/percent_used",
        }

    @staticmethod
    def _severity_for_metric(metric_key: str) -> str:
        """Return an appropriate severity level for a given metric key."""
        critical_metrics = {
            "hana_memory_utilization",
            "hana_disk_usage",
            "hana_backup_age",
            "cpu_utilization",
        }
        if metric_key in critical_metrics:
            return "CRITICAL"
        return "WARNING"
