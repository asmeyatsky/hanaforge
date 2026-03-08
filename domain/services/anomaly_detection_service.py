"""AnomalyDetectionService — pure domain logic for detecting migration execution anomalies.

Checks task execution metrics against thresholds to identify error rate spikes,
performance degradation, stalled tasks, and resource pressure.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.entities.migration_task import MigrationTask
from domain.value_objects.migration_types import (
    AnomalyAlert,
    AnomalyType,
    AuditSeverity,
    MigrationTaskStatus,
)

# ------------------------------------------------------------------
# Default thresholds — can be overridden via constructor
# ------------------------------------------------------------------
_DEFAULT_ERROR_RATE_THRESHOLD = 5  # errors within a single task execution
_DEFAULT_DURATION_MULTIPLIER = 2.0  # flag if > 2x expected duration
_DEFAULT_STALL_THRESHOLD_MINUTES = 60  # no progress for 60 minutes

# Estimated durations per task type (minutes) — mirrors task_graph_service
_EXPECTED_DURATIONS: dict[str, int] = {
    "DMO_PRECHECK": 45,
    "DMO_HANA_UPGRADE": 360,
    "DMO_SUM_EXECUTION": 480,
    "DMO_POSTCHECK": 30,
    "SDT_SHELL_CREATION": 120,
    "SDT_DATA_LOAD": 240,
    "SDT_RECONCILIATION": 90,
    "PCA_CLIENT_DELETION": 30,
    "PCA_CLIENT_COPY": 180,
    "PCA_TRANSPORT_IMPORT": 120,
    "PCA_USER_MASTER_IMPORT": 60,
    "MANUAL_CHECKPOINT": 15,
    "SYSTEM_HEALTH_CHECK": 20,
    "DATA_VALIDATION": 60,
    "CUSTOM": 60,
}


class AnomalyDetectionService:
    """Pure domain service for detecting anomalies during migration execution.

    Examines task state and execution_metrics dict to produce AnomalyAlert instances.
    """

    def __init__(
        self,
        error_rate_threshold: int = _DEFAULT_ERROR_RATE_THRESHOLD,
        duration_multiplier: float = _DEFAULT_DURATION_MULTIPLIER,
        stall_threshold_minutes: int = _DEFAULT_STALL_THRESHOLD_MINUTES,
    ) -> None:
        self._error_rate_threshold = error_rate_threshold
        self._duration_multiplier = duration_multiplier
        self._stall_threshold_minutes = stall_threshold_minutes

    def detect_anomalies(
        self,
        task: MigrationTask,
        execution_metrics: dict,
    ) -> list[AnomalyAlert]:
        """Check for anomalies given a task and its execution metrics.

        execution_metrics may contain:
          - error_count (int): number of errors during execution
          - elapsed_minutes (int): how long the task has been running
          - last_progress_minutes (int): minutes since last progress update
          - disk_usage_pct (float): disk usage percentage
          - memory_usage_pct (float): memory usage percentage
          - network_latency_ms (int): network latency in milliseconds
        """
        alerts: list[AnomalyAlert] = []
        now = datetime.now(timezone.utc)

        # 1. Error rate spike
        error_count = execution_metrics.get("error_count", 0)
        if error_count > self._error_rate_threshold:
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=task.programme_id,
                    task_id=task.id,
                    alert_type=AnomalyType.ERROR_RATE_SPIKE,
                    severity=AuditSeverity.ERROR,
                    message=(
                        f"Task '{task.task_name}' has {error_count} errors, "
                        f"exceeding threshold of {self._error_rate_threshold}"
                    ),
                    detected_at=now,
                    metric_name="error_count",
                    expected_value=float(self._error_rate_threshold),
                    actual_value=float(error_count),
                )
            )

        # 2. Performance degradation
        elapsed = execution_metrics.get("elapsed_minutes", 0)
        expected_duration = _EXPECTED_DURATIONS.get(task.task_type.value, 60)
        max_expected = expected_duration * self._duration_multiplier
        if elapsed > max_expected and task.status == MigrationTaskStatus.IN_PROGRESS:
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=task.programme_id,
                    task_id=task.id,
                    alert_type=AnomalyType.PERFORMANCE_DEGRADATION,
                    severity=AuditSeverity.WARNING,
                    message=(
                        f"Task '{task.task_name}' running for {elapsed}min, "
                        f"exceeding {self._duration_multiplier}x expected "
                        f"duration of {expected_duration}min"
                    ),
                    detected_at=now,
                    metric_name="elapsed_minutes",
                    expected_value=max_expected,
                    actual_value=float(elapsed),
                )
            )

        # 3. Task stalled
        last_progress = execution_metrics.get("last_progress_minutes")
        if (
            last_progress is not None
            and last_progress > self._stall_threshold_minutes
            and task.status == MigrationTaskStatus.IN_PROGRESS
        ):
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=task.programme_id,
                    task_id=task.id,
                    alert_type=AnomalyType.TASK_STALLED,
                    severity=AuditSeverity.CRITICAL,
                    message=(
                        f"Task '{task.task_name}' has shown no progress for "
                        f"{last_progress}min (threshold: {self._stall_threshold_minutes}min)"
                    ),
                    detected_at=now,
                    metric_name="last_progress_minutes",
                    expected_value=float(self._stall_threshold_minutes),
                    actual_value=float(last_progress),
                )
            )

        # 4. Disk space low
        disk_pct = execution_metrics.get("disk_usage_pct")
        if disk_pct is not None and disk_pct > 90.0:
            severity = AuditSeverity.CRITICAL if disk_pct > 95.0 else AuditSeverity.WARNING
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=task.programme_id,
                    task_id=task.id,
                    alert_type=AnomalyType.DISK_SPACE_LOW,
                    severity=severity,
                    message=f"Disk usage at {disk_pct}% during '{task.task_name}'",
                    detected_at=now,
                    metric_name="disk_usage_pct",
                    expected_value=90.0,
                    actual_value=disk_pct,
                )
            )

        # 5. Memory pressure
        mem_pct = execution_metrics.get("memory_usage_pct")
        if mem_pct is not None and mem_pct > 85.0:
            severity = AuditSeverity.CRITICAL if mem_pct > 95.0 else AuditSeverity.WARNING
            alerts.append(
                AnomalyAlert(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    programme_id=task.programme_id,
                    task_id=task.id,
                    alert_type=AnomalyType.MEMORY_PRESSURE,
                    severity=severity,
                    message=f"Memory usage at {mem_pct}% during '{task.task_name}'",
                    detected_at=now,
                    metric_name="memory_usage_pct",
                    expected_value=85.0,
                    actual_value=mem_pct,
                )
            )

        return alerts
