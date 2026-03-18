"""Tests for the AnomalyDetectionService — pure domain logic, no mocks."""

from datetime import datetime, timezone

import pytest

from domain.entities.migration_task import MigrationTask
from domain.services.anomaly_detection_service import AnomalyDetectionService
from domain.value_objects.migration_types import (
    AnomalyType,
    AuditSeverity,
    MigrationTaskStatus,
    MigrationTaskType,
)


def _make_task(
    *,
    status: MigrationTaskStatus = MigrationTaskStatus.IN_PROGRESS,
    task_type: MigrationTaskType = MigrationTaskType.DMO_SUM_EXECUTION,
) -> MigrationTask:
    return MigrationTask(
        id="task-anom-001",
        programme_id="prog-001",
        module="migration-orchestrator",
        task_name="SUM S/4HANA Upgrade Execution",
        description="Execute SUM upgrade",
        owner=None,
        status=status,
        depends_on=(),
        planned_start=None,
        actual_start=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        actual_end=None,
        duration_minutes=None,
        error_message=None,
        retry_count=0,
        max_retries=3,
        task_type=task_type,
        execution_params=None,
        created_at=datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def service() -> AnomalyDetectionService:
    return AnomalyDetectionService(
        error_rate_threshold=5,
        duration_multiplier=2.0,
        stall_threshold_minutes=60,
    )


class TestErrorRateSpike:
    def test_detects_error_rate_spike(self, service: AnomalyDetectionService) -> None:
        task = _make_task()
        metrics = {"error_count": 10}

        alerts = service.detect_anomalies(task, metrics)

        error_alerts = [a for a in alerts if a.alert_type == AnomalyType.ERROR_RATE_SPIKE]
        assert len(error_alerts) == 1
        alert = error_alerts[0]
        assert alert.severity == AuditSeverity.ERROR
        assert alert.expected_value == 5.0
        assert alert.actual_value == 10.0
        assert "10 errors" in alert.message
        assert alert.programme_id == "prog-001"
        assert alert.task_id == "task-anom-001"

    def test_no_alert_under_threshold(self, service: AnomalyDetectionService) -> None:
        task = _make_task()
        metrics = {"error_count": 3}

        alerts = service.detect_anomalies(task, metrics)

        error_alerts = [a for a in alerts if a.alert_type == AnomalyType.ERROR_RATE_SPIKE]
        assert len(error_alerts) == 0


class TestPerformanceDegradation:
    def test_detects_performance_degradation(self, service: AnomalyDetectionService) -> None:
        task = _make_task(task_type=MigrationTaskType.DMO_SUM_EXECUTION)
        # DMO_SUM_EXECUTION expected: 480min, threshold: 960min
        metrics = {"elapsed_minutes": 1000}

        alerts = service.detect_anomalies(task, metrics)

        perf_alerts = [a for a in alerts if a.alert_type == AnomalyType.PERFORMANCE_DEGRADATION]
        assert len(perf_alerts) == 1
        alert = perf_alerts[0]
        assert alert.severity == AuditSeverity.WARNING
        assert alert.actual_value == 1000.0

    def test_no_alert_within_threshold(self, service: AnomalyDetectionService) -> None:
        task = _make_task(task_type=MigrationTaskType.DMO_SUM_EXECUTION)
        # Within 2x the expected 480min
        metrics = {"elapsed_minutes": 500}

        alerts = service.detect_anomalies(task, metrics)

        perf_alerts = [a for a in alerts if a.alert_type == AnomalyType.PERFORMANCE_DEGRADATION]
        assert len(perf_alerts) == 0

    def test_no_degradation_for_completed_task(self, service: AnomalyDetectionService) -> None:
        """Performance degradation only triggers for IN_PROGRESS tasks."""
        task = _make_task(status=MigrationTaskStatus.COMPLETED)
        metrics = {"elapsed_minutes": 1000}

        alerts = service.detect_anomalies(task, metrics)

        perf_alerts = [a for a in alerts if a.alert_type == AnomalyType.PERFORMANCE_DEGRADATION]
        assert len(perf_alerts) == 0


class TestTaskStalled:
    def test_detects_stalled_task(self, service: AnomalyDetectionService) -> None:
        task = _make_task()
        metrics = {"last_progress_minutes": 90}

        alerts = service.detect_anomalies(task, metrics)

        stall_alerts = [a for a in alerts if a.alert_type == AnomalyType.TASK_STALLED]
        assert len(stall_alerts) == 1
        alert = stall_alerts[0]
        assert alert.severity == AuditSeverity.CRITICAL
        assert alert.actual_value == 90.0

    def test_no_stall_under_threshold(self, service: AnomalyDetectionService) -> None:
        task = _make_task()
        metrics = {"last_progress_minutes": 30}

        alerts = service.detect_anomalies(task, metrics)

        stall_alerts = [a for a in alerts if a.alert_type == AnomalyType.TASK_STALLED]
        assert len(stall_alerts) == 0


class TestNormalExecution:
    def test_no_anomaly_for_normal_execution(self, service: AnomalyDetectionService) -> None:
        task = _make_task(task_type=MigrationTaskType.DMO_PRECHECK)
        metrics = {
            "error_count": 1,
            "elapsed_minutes": 30,
            "last_progress_minutes": 2,
            "disk_usage_pct": 55.0,
            "memory_usage_pct": 60.0,
        }

        alerts = service.detect_anomalies(task, metrics)

        assert len(alerts) == 0


class TestResourcePressure:
    def test_detects_disk_space_low(self, service: AnomalyDetectionService) -> None:
        task = _make_task()
        metrics = {"disk_usage_pct": 92.0}

        alerts = service.detect_anomalies(task, metrics)

        disk_alerts = [a for a in alerts if a.alert_type == AnomalyType.DISK_SPACE_LOW]
        assert len(disk_alerts) == 1
        assert disk_alerts[0].severity == AuditSeverity.WARNING

    def test_detects_critical_disk_space(self, service: AnomalyDetectionService) -> None:
        task = _make_task()
        metrics = {"disk_usage_pct": 97.0}

        alerts = service.detect_anomalies(task, metrics)

        disk_alerts = [a for a in alerts if a.alert_type == AnomalyType.DISK_SPACE_LOW]
        assert len(disk_alerts) == 1
        assert disk_alerts[0].severity == AuditSeverity.CRITICAL

    def test_detects_memory_pressure(self, service: AnomalyDetectionService) -> None:
        task = _make_task()
        metrics = {"memory_usage_pct": 90.0}

        alerts = service.detect_anomalies(task, metrics)

        mem_alerts = [a for a in alerts if a.alert_type == AnomalyType.MEMORY_PRESSURE]
        assert len(mem_alerts) == 1
        assert mem_alerts[0].severity == AuditSeverity.WARNING

    def test_multiple_anomalies_at_once(self, service: AnomalyDetectionService) -> None:
        """Multiple anomalies can be detected in a single pass."""
        task = _make_task()
        metrics = {
            "error_count": 10,
            "elapsed_minutes": 1200,
            "last_progress_minutes": 120,
            "disk_usage_pct": 96.0,
            "memory_usage_pct": 97.0,
        }

        alerts = service.detect_anomalies(task, metrics)

        alert_types = {a.alert_type for a in alerts}
        assert AnomalyType.ERROR_RATE_SPIKE in alert_types
        assert AnomalyType.PERFORMANCE_DEGRADATION in alert_types
        assert AnomalyType.TASK_STALLED in alert_types
        assert AnomalyType.DISK_SPACE_LOW in alert_types
        assert AnomalyType.MEMORY_PRESSURE in alert_types
        assert len(alerts) == 5
