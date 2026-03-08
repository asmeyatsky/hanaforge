"""Migration orchestrator value objects — task statuses, types, anomaly alerts, and health metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MigrationTaskStatus(Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class MigrationTaskType(Enum):
    DMO_PRECHECK = "DMO_PRECHECK"
    DMO_HANA_UPGRADE = "DMO_HANA_UPGRADE"
    DMO_SUM_EXECUTION = "DMO_SUM_EXECUTION"
    DMO_POSTCHECK = "DMO_POSTCHECK"
    SDT_SHELL_CREATION = "SDT_SHELL_CREATION"
    SDT_DATA_LOAD = "SDT_DATA_LOAD"
    SDT_RECONCILIATION = "SDT_RECONCILIATION"
    PCA_CLIENT_DELETION = "PCA_CLIENT_DELETION"
    PCA_CLIENT_COPY = "PCA_CLIENT_COPY"
    PCA_TRANSPORT_IMPORT = "PCA_TRANSPORT_IMPORT"
    PCA_USER_MASTER_IMPORT = "PCA_USER_MASTER_IMPORT"
    MANUAL_CHECKPOINT = "MANUAL_CHECKPOINT"
    SYSTEM_HEALTH_CHECK = "SYSTEM_HEALTH_CHECK"
    DATA_VALIDATION = "DATA_VALIDATION"
    CUSTOM = "CUSTOM"


class AuditAction(Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_RETRIED = "TASK_RETRIED"
    TASK_BLOCKED = "TASK_BLOCKED"
    TASK_SKIPPED = "TASK_SKIPPED"
    MIGRATION_STARTED = "MIGRATION_STARTED"
    MIGRATION_COMPLETED = "MIGRATION_COMPLETED"
    MIGRATION_PAUSED = "MIGRATION_PAUSED"
    MIGRATION_ROLLED_BACK = "MIGRATION_ROLLED_BACK"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    HEALTH_CHECK_PASSED = "HEALTH_CHECK_PASSED"
    HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_DENIED = "APPROVAL_DENIED"


class AuditSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AnomalyType(Enum):
    ERROR_RATE_SPIKE = "ERROR_RATE_SPIKE"
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    TASK_STALLED = "TASK_STALLED"
    DISK_SPACE_LOW = "DISK_SPACE_LOW"
    MEMORY_PRESSURE = "MEMORY_PRESSURE"
    NETWORK_LATENCY = "NETWORK_LATENCY"
    DATA_MISMATCH = "DATA_MISMATCH"
    UNEXPECTED_RESTART = "UNEXPECTED_RESTART"


@dataclass(frozen=True)
class AnomalyAlert:
    """An anomaly detected during migration execution."""

    id: str
    programme_id: str
    task_id: str | None
    alert_type: AnomalyType
    severity: AuditSeverity
    message: str
    detected_at: datetime
    metric_name: str | None = None
    expected_value: float | None = None
    actual_value: float | None = None
    acknowledged: bool = False


@dataclass(frozen=True)
class CriticalPathInfo:
    """Critical path analysis results for a migration task graph."""

    total_duration_minutes: int
    critical_tasks: tuple[str, ...]
    slack_per_task: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class MigrationHealth:
    """Overall health snapshot of a running migration."""

    overall_status: str  # GREEN, AMBER, RED
    tasks_completed: int
    tasks_in_progress: int
    tasks_pending: int
    tasks_failed: int
    active_anomalies: int
    critical_path_deviation_minutes: int
    last_updated: datetime
