"""Tests for the TaskGraphService — task graph generation and critical path analysis."""

from datetime import datetime, timezone

import pytest

from domain.entities.migration_task import MigrationTask
from domain.services.task_graph_service import TaskGraphService
from domain.value_objects.migration_approach import MigrationApproach
from domain.value_objects.migration_types import (
    AnomalyAlert,
    AnomalyType,
    AuditSeverity,
    CriticalPathInfo,
    MigrationHealth,
    MigrationTaskStatus,
    MigrationTaskType,
)


@pytest.fixture
def service() -> TaskGraphService:
    return TaskGraphService()


# ------------------------------------------------------------------
# Task graph generation
# ------------------------------------------------------------------


class TestBrownfieldTaskGraph:
    def test_brownfield_task_graph_generation(self, service: TaskGraphService) -> None:
        tasks = service.build_task_graph(
            programme_id="prog-001",
            approach=MigrationApproach.BROWNFIELD,
            landscape_metadata={"db_size_gb": 500},
        )

        assert len(tasks) > 0

        # Should follow the sequence:
        # DMO_PRECHECK -> DMO_HANA_UPGRADE -> DMO_SUM_EXECUTION -> DMO_POSTCHECK
        # -> PCA chain -> health check -> manual checkpoint
        task_types = [t.task_type for t in tasks]

        assert MigrationTaskType.DMO_PRECHECK in task_types
        assert MigrationTaskType.DMO_HANA_UPGRADE in task_types
        assert MigrationTaskType.DMO_SUM_EXECUTION in task_types
        assert MigrationTaskType.DMO_POSTCHECK in task_types
        assert MigrationTaskType.PCA_CLIENT_DELETION in task_types
        assert MigrationTaskType.PCA_CLIENT_COPY in task_types
        assert MigrationTaskType.PCA_TRANSPORT_IMPORT in task_types
        assert MigrationTaskType.PCA_USER_MASTER_IMPORT in task_types
        assert MigrationTaskType.SYSTEM_HEALTH_CHECK in task_types
        assert MigrationTaskType.MANUAL_CHECKPOINT in task_types

        # First task should have no dependencies
        precheck = next(t for t in tasks if t.task_type == MigrationTaskType.DMO_PRECHECK)
        assert precheck.depends_on == ()

        # HANA upgrade depends on precheck
        hana = next(t for t in tasks if t.task_type == MigrationTaskType.DMO_HANA_UPGRADE)
        assert precheck.id in hana.depends_on

        # SUM depends on HANA upgrade
        sum_task = next(t for t in tasks if t.task_type == MigrationTaskType.DMO_SUM_EXECUTION)
        assert hana.id in sum_task.depends_on

        # Post-check depends on SUM
        postcheck = next(t for t in tasks if t.task_type == MigrationTaskType.DMO_POSTCHECK)
        assert sum_task.id in postcheck.depends_on

    def test_all_tasks_have_unique_ids(self, service: TaskGraphService) -> None:
        tasks = service.build_task_graph(
            programme_id="prog-001",
            approach=MigrationApproach.BROWNFIELD,
            landscape_metadata={},
        )

        ids = [t.id for t in tasks]
        assert len(ids) == len(set(ids))

    def test_all_tasks_are_pending(self, service: TaskGraphService) -> None:
        tasks = service.build_task_graph(
            programme_id="prog-001",
            approach=MigrationApproach.BROWNFIELD,
            landscape_metadata={},
        )

        for task in tasks:
            assert task.status == MigrationTaskStatus.PENDING


class TestSDTTaskGraph:
    def test_sdt_task_graph_with_parallel_data_loads(self, service: TaskGraphService) -> None:
        data_domains = ["FI", "CO", "MM", "SD", "PP"]
        tasks = service.build_task_graph(
            programme_id="prog-002",
            approach=MigrationApproach.SELECTIVE_DATA_TRANSITION,
            landscape_metadata={"data_domains": data_domains},
        )

        assert len(tasks) > 0

        # Should have SDT_SHELL_CREATION
        shell = next(t for t in tasks if t.task_type == MigrationTaskType.SDT_SHELL_CREATION)
        assert shell.depends_on == ()

        # Should have parallel data loads — one per domain
        data_loads = [t for t in tasks if t.task_type == MigrationTaskType.SDT_DATA_LOAD]
        assert len(data_loads) == len(data_domains)

        # Each data load depends on shell creation
        for dl in data_loads:
            assert shell.id in dl.depends_on

        # Reconciliation depends on ALL data loads
        recon = next(t for t in tasks if t.task_type == MigrationTaskType.SDT_RECONCILIATION)
        for dl in data_loads:
            assert dl.id in recon.depends_on

    def test_sdt_default_domains(self, service: TaskGraphService) -> None:
        tasks = service.build_task_graph(
            programme_id="prog-002",
            approach=MigrationApproach.SELECTIVE_DATA_TRANSITION,
            landscape_metadata={},
        )

        data_loads = [t for t in tasks if t.task_type == MigrationTaskType.SDT_DATA_LOAD]
        # Default domains: FI, CO, MM, SD
        assert len(data_loads) == 4


class TestGreenfieldTaskGraph:
    def test_greenfield_task_graph(self, service: TaskGraphService) -> None:
        tasks = service.build_task_graph(
            programme_id="prog-003",
            approach=MigrationApproach.GREENFIELD,
            landscape_metadata={},
        )

        assert len(tasks) > 0

        task_types = [t.task_type for t in tasks]
        assert MigrationTaskType.PCA_CLIENT_COPY in task_types
        assert MigrationTaskType.PCA_TRANSPORT_IMPORT in task_types
        assert MigrationTaskType.PCA_USER_MASTER_IMPORT in task_types
        assert MigrationTaskType.DATA_VALIDATION in task_types
        assert MigrationTaskType.SYSTEM_HEALTH_CHECK in task_types
        assert MigrationTaskType.MANUAL_CHECKPOINT in task_types

        # DMO tasks should NOT be present
        assert MigrationTaskType.DMO_PRECHECK not in task_types
        assert MigrationTaskType.DMO_HANA_UPGRADE not in task_types
        assert MigrationTaskType.DMO_SUM_EXECUTION not in task_types

        # First task should have no dependencies
        client_copy = tasks[0]
        assert client_copy.depends_on == ()
        assert client_copy.task_type == MigrationTaskType.PCA_CLIENT_COPY


class TestTaskDependencies:
    def test_task_dependencies_are_valid(self, service: TaskGraphService) -> None:
        """All dependency IDs must reference tasks that exist in the graph."""
        for approach in [
            MigrationApproach.BROWNFIELD,
            MigrationApproach.SELECTIVE_DATA_TRANSITION,
            MigrationApproach.GREENFIELD,
        ]:
            tasks = service.build_task_graph(
                programme_id="prog-validate",
                approach=approach,
                landscape_metadata={"data_domains": ["FI", "CO", "MM"]},
            )

            task_ids = {t.id for t in tasks}
            for task in tasks:
                for dep_id in task.depends_on:
                    assert dep_id in task_ids, (
                        f"Task '{task.task_name}' depends on unknown task '{dep_id}' in {approach.value} graph"
                    )


# ------------------------------------------------------------------
# Critical path analysis
# ------------------------------------------------------------------


class TestCriticalPath:
    def test_critical_path_calculation(self, service: TaskGraphService) -> None:
        """Test the forward/backward pass algorithm on a known graph."""
        tasks = service.build_task_graph(
            programme_id="prog-cp",
            approach=MigrationApproach.BROWNFIELD,
            landscape_metadata={},
        )

        cp = service.calculate_critical_path(tasks)

        assert isinstance(cp, CriticalPathInfo)
        assert cp.total_duration_minutes > 0
        assert len(cp.critical_tasks) > 0
        assert len(cp.slack_per_task) == len(tasks)

        # Critical tasks should have zero slack
        slack_map = dict(cp.slack_per_task)
        for ct_id in cp.critical_tasks:
            assert slack_map[ct_id] == 0, f"Critical task {ct_id} should have zero slack"

        # Non-critical tasks should have slack >= 0
        for task_id, slack in cp.slack_per_task:
            assert slack >= 0, f"Task {task_id} has negative slack: {slack}"

    def test_critical_path_linear_chain(self, service: TaskGraphService) -> None:
        """A linear chain should have all tasks on the critical path."""
        tasks = service.build_task_graph(
            programme_id="prog-linear",
            approach=MigrationApproach.GREENFIELD,
            landscape_metadata={},
        )

        cp = service.calculate_critical_path(tasks)

        # Greenfield is a linear chain — all tasks should be critical
        assert len(cp.critical_tasks) == len(tasks)

    def test_critical_path_with_parallel_branches(self, service: TaskGraphService) -> None:
        """SDT graph has parallel data loads — critical path includes parallel tasks
        that all have the same estimated duration (zero slack among equals)."""
        tasks = service.build_task_graph(
            programme_id="prog-parallel",
            approach=MigrationApproach.SELECTIVE_DATA_TRANSITION,
            landscape_metadata={"data_domains": ["FI", "CO", "MM", "SD"]},
        )

        cp = service.calculate_critical_path(tasks)

        # All parallel data loads have the same estimated duration, so all
        # have zero slack and are on the critical path. The total duration
        # equals the single-branch duration (not the sum of all branches).
        data_loads = [t for t in tasks if t.task_type == MigrationTaskType.SDT_DATA_LOAD]
        critical_data_loads = [dl for dl in data_loads if dl.id in cp.critical_tasks]
        assert len(critical_data_loads) == len(data_loads)

        # All data load tasks should have zero slack (equal parallel branches)
        slack_map = dict(cp.slack_per_task)
        for dl in data_loads:
            assert slack_map[dl.id] == 0

    def test_empty_task_list(self, service: TaskGraphService) -> None:
        cp = service.calculate_critical_path([])

        assert cp.total_duration_minutes == 0
        assert cp.critical_tasks == ()
        assert cp.slack_per_task == ()


# ------------------------------------------------------------------
# Migration health
# ------------------------------------------------------------------


class TestMigrationHealth:
    def _make_completed_task(self, task_id: str) -> MigrationTask:
        return MigrationTask(
            id=task_id,
            programme_id="prog-health",
            module="migration-orchestrator",
            task_name=f"Task {task_id}",
            description="Test task",
            owner=None,
            status=MigrationTaskStatus.COMPLETED,
            depends_on=(),
            planned_start=None,
            actual_start=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            actual_end=datetime(2026, 3, 1, 11, 0, 0, tzinfo=timezone.utc),
            duration_minutes=45,
            error_message=None,
            retry_count=0,
            max_retries=3,
            task_type=MigrationTaskType.DMO_PRECHECK,
            execution_params=None,
            created_at=datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
        )

    def _make_pending_task(self, task_id: str) -> MigrationTask:
        return MigrationTask(
            id=task_id,
            programme_id="prog-health",
            module="migration-orchestrator",
            task_name=f"Task {task_id}",
            description="Test task",
            owner=None,
            status=MigrationTaskStatus.PENDING,
            depends_on=(),
            planned_start=None,
            actual_start=None,
            actual_end=None,
            duration_minutes=None,
            error_message=None,
            retry_count=0,
            max_retries=3,
            task_type=MigrationTaskType.DMO_PRECHECK,
            execution_params=None,
            created_at=datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
        )

    def _make_failed_task(self, task_id: str) -> MigrationTask:
        return MigrationTask(
            id=task_id,
            programme_id="prog-health",
            module="migration-orchestrator",
            task_name=f"Task {task_id}",
            description="Test task",
            owner=None,
            status=MigrationTaskStatus.FAILED,
            depends_on=(),
            planned_start=None,
            actual_start=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            actual_end=datetime(2026, 3, 1, 10, 30, 0, tzinfo=timezone.utc),
            duration_minutes=None,
            error_message="Failure",
            retry_count=0,
            max_retries=3,
            task_type=MigrationTaskType.DMO_PRECHECK,
            execution_params=None,
            created_at=datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
        )

    def test_migration_health_green(self, service: TaskGraphService) -> None:
        tasks = [
            self._make_completed_task("t-1"),
            self._make_completed_task("t-2"),
            self._make_pending_task("t-3"),
        ]
        anomalies: list[AnomalyAlert] = []

        health = service.calculate_migration_health(tasks, anomalies)

        assert isinstance(health, MigrationHealth)
        assert health.overall_status == "GREEN"
        assert health.tasks_completed == 2
        assert health.tasks_pending == 1
        assert health.tasks_failed == 0
        assert health.active_anomalies == 0

    def test_migration_health_red_on_failures(self, service: TaskGraphService) -> None:
        tasks = [
            self._make_completed_task("t-1"),
            self._make_failed_task("t-2"),
            self._make_pending_task("t-3"),
        ]
        anomalies: list[AnomalyAlert] = []

        health = service.calculate_migration_health(tasks, anomalies)

        assert health.overall_status == "RED"
        assert health.tasks_failed == 1

    def test_migration_health_amber_on_anomalies(self, service: TaskGraphService) -> None:
        tasks = [
            self._make_completed_task("t-1"),
            self._make_pending_task("t-2"),
        ]
        anomalies = [
            AnomalyAlert(
                id="alert-1",
                programme_id="prog-health",
                task_id="t-1",
                alert_type=AnomalyType.PERFORMANCE_DEGRADATION,
                severity=AuditSeverity.WARNING,
                message="Slow task",
                detected_at=datetime(2026, 3, 1, 11, 0, 0, tzinfo=timezone.utc),
                acknowledged=False,
            ),
        ]

        health = service.calculate_migration_health(tasks, anomalies)

        assert health.overall_status == "AMBER"
        assert health.active_anomalies == 1

    def test_migration_health_red_on_many_anomalies(self, service: TaskGraphService) -> None:
        tasks = [self._make_pending_task("t-1")]
        anomalies = [
            AnomalyAlert(
                id=f"alert-{i}",
                programme_id="prog-health",
                task_id=None,
                alert_type=AnomalyType.ERROR_RATE_SPIKE,
                severity=AuditSeverity.ERROR,
                message=f"Alert {i}",
                detected_at=datetime(2026, 3, 1, 11, 0, 0, tzinfo=timezone.utc),
                acknowledged=False,
            )
            for i in range(3)
        ]

        health = service.calculate_migration_health(tasks, anomalies)

        assert health.overall_status == "RED"
        assert health.active_anomalies == 3
