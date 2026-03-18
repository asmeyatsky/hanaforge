"""AIAnomalyDetectionAdapter — threshold-based anomaly detection implementing AnomalyDetectionPort.

Uses simple statistical thresholds for anomaly detection. Designed to be
upgraded to Claude-powered detection in production.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.value_objects.migration_types import (
    AnomalyAlert,
    AnomalyType,
    AuditSeverity,
)

# ------------------------------------------------------------------
# Default thresholds
# ------------------------------------------------------------------
_ERROR_RATE_THRESHOLD = 5
_STALL_THRESHOLD_MINUTES = 60
_DISK_THRESHOLD_PCT = 90.0
_MEMORY_THRESHOLD_PCT = 85.0
_LATENCY_THRESHOLD_MS = 500


class AIAnomalyDetectionAdapter:
    """Implements AnomalyDetectionPort with threshold-based detection.

    Analyzes aggregated programme-level metrics and returns anomaly alerts.
    """

    def __init__(
        self,
        error_rate_threshold: int = _ERROR_RATE_THRESHOLD,
        stall_threshold_minutes: int = _STALL_THRESHOLD_MINUTES,
        disk_threshold_pct: float = _DISK_THRESHOLD_PCT,
        memory_threshold_pct: float = _MEMORY_THRESHOLD_PCT,
        latency_threshold_ms: int = _LATENCY_THRESHOLD_MS,
    ) -> None:
        self._error_rate_threshold = error_rate_threshold
        self._stall_threshold_minutes = stall_threshold_minutes
        self._disk_threshold_pct = disk_threshold_pct
        self._memory_threshold_pct = memory_threshold_pct
        self._latency_threshold_ms = latency_threshold_ms

    async def analyze_metrics(
        self, programme_id: str, metrics: dict
    ) -> list[AnomalyAlert]:
        """Analyze aggregated metrics for a programme and return anomaly alerts.

        Expected metrics dict keys:
          - total_errors (int)
          - avg_task_duration_minutes (float)
          - expected_avg_duration_minutes (float)
          - stalled_task_count (int)
          - disk_usage_pct (float)
          - memory_usage_pct (float)
          - network_latency_ms (int)
          - data_mismatch_count (int)
          - unexpected_restarts (int)
        """
        alerts: list[AnomalyAlert] = []
        now = datetime.now(timezone.utc)

        # Error rate spike
        total_errors = metrics.get("total_errors", 0)
        if total_errors > self._error_rate_threshold:
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=programme_id,
                    task_id=None,
                    alert_type=AnomalyType.ERROR_RATE_SPIKE,
                    severity=AuditSeverity.ERROR,
                    message=(
                        f"Programme error rate spike: {total_errors} errors "
                        f"(threshold: {self._error_rate_threshold})"
                    ),
                    detected_at=now,
                    metric_name="total_errors",
                    expected_value=float(self._error_rate_threshold),
                    actual_value=float(total_errors),
                )
            )

        # Performance degradation
        avg_duration = metrics.get("avg_task_duration_minutes", 0)
        expected_duration = metrics.get("expected_avg_duration_minutes", 0)
        if expected_duration > 0 and avg_duration > expected_duration * 2:
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=programme_id,
                    task_id=None,
                    alert_type=AnomalyType.PERFORMANCE_DEGRADATION,
                    severity=AuditSeverity.WARNING,
                    message=(
                        f"Average task duration {avg_duration:.0f}min exceeds "
                        f"2x expected {expected_duration:.0f}min"
                    ),
                    detected_at=now,
                    metric_name="avg_task_duration_minutes",
                    expected_value=expected_duration * 2,
                    actual_value=avg_duration,
                )
            )

        # Stalled tasks
        stalled = metrics.get("stalled_task_count", 0)
        if stalled > 0:
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=programme_id,
                    task_id=None,
                    alert_type=AnomalyType.TASK_STALLED,
                    severity=AuditSeverity.CRITICAL,
                    message=f"{stalled} task(s) appear stalled (no progress for >{self._stall_threshold_minutes}min)",
                    detected_at=now,
                    metric_name="stalled_task_count",
                    expected_value=0.0,
                    actual_value=float(stalled),
                )
            )

        # Disk space
        disk_pct = metrics.get("disk_usage_pct", 0.0)
        if disk_pct > self._disk_threshold_pct:
            severity = AuditSeverity.CRITICAL if disk_pct > 95.0 else AuditSeverity.WARNING
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=programme_id,
                    task_id=None,
                    alert_type=AnomalyType.DISK_SPACE_LOW,
                    severity=severity,
                    message=f"Disk usage at {disk_pct:.1f}%",
                    detected_at=now,
                    metric_name="disk_usage_pct",
                    expected_value=self._disk_threshold_pct,
                    actual_value=disk_pct,
                )
            )

        # Memory pressure
        mem_pct = metrics.get("memory_usage_pct", 0.0)
        if mem_pct > self._memory_threshold_pct:
            severity = AuditSeverity.CRITICAL if mem_pct > 95.0 else AuditSeverity.WARNING
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=programme_id,
                    task_id=None,
                    alert_type=AnomalyType.MEMORY_PRESSURE,
                    severity=severity,
                    message=f"Memory usage at {mem_pct:.1f}%",
                    detected_at=now,
                    metric_name="memory_usage_pct",
                    expected_value=self._memory_threshold_pct,
                    actual_value=mem_pct,
                )
            )

        # Network latency
        latency = metrics.get("network_latency_ms", 0)
        if latency > self._latency_threshold_ms:
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=programme_id,
                    task_id=None,
                    alert_type=AnomalyType.NETWORK_LATENCY,
                    severity=AuditSeverity.WARNING,
                    message=f"Network latency at {latency}ms (threshold: {self._latency_threshold_ms}ms)",
                    detected_at=now,
                    metric_name="network_latency_ms",
                    expected_value=float(self._latency_threshold_ms),
                    actual_value=float(latency),
                )
            )

        # Data mismatch
        mismatches = metrics.get("data_mismatch_count", 0)
        if mismatches > 0:
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=programme_id,
                    task_id=None,
                    alert_type=AnomalyType.DATA_MISMATCH,
                    severity=AuditSeverity.ERROR,
                    message=f"{mismatches} data mismatch(es) detected during reconciliation",
                    detected_at=now,
                    metric_name="data_mismatch_count",
                    expected_value=0.0,
                    actual_value=float(mismatches),
                )
            )

        # Unexpected restarts
        restarts = metrics.get("unexpected_restarts", 0)
        if restarts > 0:
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=programme_id,
                    task_id=None,
                    alert_type=AnomalyType.UNEXPECTED_RESTART,
                    severity=AuditSeverity.CRITICAL,
                    message=f"{restarts} unexpected system restart(s) detected",
                    detected_at=now,
                    metric_name="unexpected_restarts",
                    expected_value=0.0,
                    actual_value=float(restarts),
                )
            )

        return alerts
