"""TaskGraphService — pure domain logic for building migration task DAGs and critical path analysis.

Generates realistic SAP migration task sequences based on the chosen migration
approach (Brownfield DMO, Selective Data Transition, or Greenfield).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from domain.entities.migration_task import MigrationTask
from domain.value_objects.migration_approach import MigrationApproach
from domain.value_objects.migration_types import (
    AnomalyAlert,
    CriticalPathInfo,
    MigrationHealth,
    MigrationTaskStatus,
    MigrationTaskType,
)

# ------------------------------------------------------------------
# Estimated durations per task type (minutes) for critical path
# ------------------------------------------------------------------
_DEFAULT_DURATIONS: dict[MigrationTaskType, int] = {
    MigrationTaskType.DMO_PRECHECK: 45,
    MigrationTaskType.DMO_HANA_UPGRADE: 360,
    MigrationTaskType.DMO_SUM_EXECUTION: 480,
    MigrationTaskType.DMO_POSTCHECK: 30,
    MigrationTaskType.SDT_SHELL_CREATION: 120,
    MigrationTaskType.SDT_DATA_LOAD: 240,
    MigrationTaskType.SDT_RECONCILIATION: 90,
    MigrationTaskType.PCA_CLIENT_DELETION: 30,
    MigrationTaskType.PCA_CLIENT_COPY: 180,
    MigrationTaskType.PCA_TRANSPORT_IMPORT: 120,
    MigrationTaskType.PCA_USER_MASTER_IMPORT: 60,
    MigrationTaskType.MANUAL_CHECKPOINT: 15,
    MigrationTaskType.SYSTEM_HEALTH_CHECK: 20,
    MigrationTaskType.DATA_VALIDATION: 60,
    MigrationTaskType.CUSTOM: 60,
}


def _task_id() -> str:
    return f"task-{uuid.uuid4().hex[:12]}"


def _make_task(
    *,
    programme_id: str,
    module: str,
    task_name: str,
    description: str,
    task_type: MigrationTaskType,
    depends_on: tuple[str, ...] = (),
    execution_params: tuple[tuple[str, str], ...] | None = None,
) -> MigrationTask:
    return MigrationTask(
        id=_task_id(),
        programme_id=programme_id,
        module=module,
        task_name=task_name,
        description=description,
        owner=None,
        status=MigrationTaskStatus.PENDING,
        depends_on=depends_on,
        planned_start=None,
        actual_start=None,
        actual_end=None,
        duration_minutes=None,
        error_message=None,
        retry_count=0,
        max_retries=3,
        task_type=task_type,
        execution_params=execution_params,
        created_at=datetime.now(timezone.utc),
    )


class TaskGraphService:
    """Pure domain service — builds migration task DAGs and computes critical path."""

    # ------------------------------------------------------------------
    # Task graph generation
    # ------------------------------------------------------------------

    def build_task_graph(
        self,
        programme_id: str,
        approach: MigrationApproach,
        landscape_metadata: dict,
    ) -> list[MigrationTask]:
        """Generate the full task DAG based on migration approach.

        landscape_metadata may contain:
          - data_domains: list of business domains for parallel data loads
          - db_size_gb: database size affecting estimated durations
          - system_count: number of systems in the landscape
        """
        if approach == MigrationApproach.BROWNFIELD:
            return self._build_brownfield_graph(programme_id, landscape_metadata)
        if approach == MigrationApproach.SELECTIVE_DATA_TRANSITION:
            return self._build_sdt_graph(programme_id, landscape_metadata)
        if approach in (MigrationApproach.GREENFIELD, MigrationApproach.RISE_WITH_SAP):
            return self._build_greenfield_graph(programme_id, landscape_metadata)
        raise ValueError(f"Unsupported migration approach: {approach.value}")

    # ------------------------------------------------------------------
    # Brownfield (DMO) graph
    # ------------------------------------------------------------------

    def _build_brownfield_graph(self, programme_id: str, metadata: dict) -> list[MigrationTask]:
        tasks: list[MigrationTask] = []

        # Phase 1: DMO Pre-checks
        precheck = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="DMO Pre-Migration Checks",
            description=(
                "Execute SAP Maintenance Planner checks, verify ABAP compatibility, "
                "check database consistency, validate system prerequisites for HANA migration"
            ),
            task_type=MigrationTaskType.DMO_PRECHECK,
            execution_params=(
                ("check_type", "full"),
                ("verify_abap_compat", "true"),
                ("verify_db_consistency", "true"),
            ),
        )
        tasks.append(precheck)

        # Phase 2: HANA DB Migration
        hana_upgrade = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="HANA Database Migration",
            description=(
                "Execute Database Migration Option — convert source database to SAP HANA. "
                "Includes tablespace reorganisation, data migration, and index rebuild."
            ),
            task_type=MigrationTaskType.DMO_HANA_UPGRADE,
            depends_on=(precheck.id,),
            execution_params=(
                ("migration_mode", "DMO"),
                ("target_db", "HANA"),
            ),
        )
        tasks.append(hana_upgrade)

        # Phase 3: SUM Execution (Software Update Manager)
        sum_exec = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="SUM S/4HANA Upgrade Execution",
            description=(
                "Execute Software Update Manager to upgrade from ECC to S/4HANA. "
                "Includes SPDD/SPAU adjustments, simplification item checks, "
                "and data conversion of affected tables (BSEG, ACDOCA, MATDOC)."
            ),
            task_type=MigrationTaskType.DMO_SUM_EXECUTION,
            depends_on=(hana_upgrade.id,),
            execution_params=(
                ("target_release", "S4HANA_2023"),
                ("sum_mode", "standard"),
            ),
        )
        tasks.append(sum_exec)

        # Phase 4: DMO Post-checks
        postcheck = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="DMO Post-Migration Checks",
            description=(
                "Validate data integrity after DMO conversion. Verify ACDOCA migration, "
                "material ledger activation, business partner migration status."
            ),
            task_type=MigrationTaskType.DMO_POSTCHECK,
            depends_on=(sum_exec.id,),
        )
        tasks.append(postcheck)

        # Phase 5: PCA tasks
        pca_tasks = self._build_pca_tasks(programme_id, depends_on=(postcheck.id,))
        tasks.extend(pca_tasks)

        # Phase 6: Final validation and checkpoint
        last_pca_id = pca_tasks[-1].id if pca_tasks else postcheck.id
        final_tasks = self._build_final_tasks(programme_id, depends_on=(last_pca_id,))
        tasks.extend(final_tasks)

        return tasks

    # ------------------------------------------------------------------
    # Selective Data Transition graph
    # ------------------------------------------------------------------

    def _build_sdt_graph(self, programme_id: str, metadata: dict) -> list[MigrationTask]:
        tasks: list[MigrationTask] = []

        # Phase 1: Shell system creation
        shell = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="SDT Shell System Creation",
            description=(
                "Create target S/4HANA shell system using system copy. "
                "Includes initial configuration, organisational structure setup, "
                "and master data framework preparation."
            ),
            task_type=MigrationTaskType.SDT_SHELL_CREATION,
            execution_params=(
                ("shell_type", "new_install"),
                ("config_template", "standard"),
            ),
        )
        tasks.append(shell)

        # Phase 2: Parallel data loads per business domain
        data_domains = metadata.get("data_domains", ["FI", "CO", "MM", "SD"])
        data_load_tasks: list[MigrationTask] = []

        for domain in data_domains:
            data_load = _make_task(
                programme_id=programme_id,
                module="migration-orchestrator",
                task_name=f"SDT Data Load — {domain}",
                description=(
                    f"Load {domain} business data into the target shell system. "
                    f"Includes master data, transactional data, and configuration objects "
                    f"for the {domain} module."
                ),
                task_type=MigrationTaskType.SDT_DATA_LOAD,
                depends_on=(shell.id,),
                execution_params=(
                    ("business_domain", domain),
                    ("load_mode", "delta_capable"),
                ),
            )
            data_load_tasks.append(data_load)
            tasks.append(data_load)

        # Phase 3: Reconciliation (depends on ALL data loads)
        data_load_ids = tuple(t.id for t in data_load_tasks)
        reconciliation = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="SDT Data Reconciliation",
            description=(
                "Reconcile migrated data against source system. Verify record counts, "
                "financial balances, material stocks, and cross-module referential integrity."
            ),
            task_type=MigrationTaskType.SDT_RECONCILIATION,
            depends_on=data_load_ids,
            execution_params=(
                ("reconciliation_type", "full"),
                ("tolerance_pct", "0.01"),
            ),
        )
        tasks.append(reconciliation)

        # Phase 4: PCA tasks
        pca_tasks = self._build_pca_tasks(programme_id, depends_on=(reconciliation.id,))
        tasks.extend(pca_tasks)

        # Phase 5: Final validation and checkpoint
        last_pca_id = pca_tasks[-1].id if pca_tasks else reconciliation.id
        final_tasks = self._build_final_tasks(programme_id, depends_on=(last_pca_id,))
        tasks.extend(final_tasks)

        return tasks

    # ------------------------------------------------------------------
    # Greenfield graph
    # ------------------------------------------------------------------

    def _build_greenfield_graph(self, programme_id: str, metadata: dict) -> list[MigrationTask]:
        tasks: list[MigrationTask] = []

        # Phase 1: Client copy — initial system preparation
        client_copy = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="PCA Client Copy",
            description=(
                "Execute client copy (SCC9/SCCL) to prepare target client. "
                "Copy customising, cross-client settings, and user master records."
            ),
            task_type=MigrationTaskType.PCA_CLIENT_COPY,
            execution_params=(
                ("source_client", "000"),
                ("target_client", "100"),
                ("copy_profile", "SAP_CUST"),
            ),
        )
        tasks.append(client_copy)

        # Phase 2: Transport import
        transport_import = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="PCA Transport Import",
            description=(
                "Import transport requests in correct sequence — customising, "
                "workbench, and ABAP transports. Validate import logs for RC <= 4."
            ),
            task_type=MigrationTaskType.PCA_TRANSPORT_IMPORT,
            depends_on=(client_copy.id,),
            execution_params=(
                ("import_mode", "sequential"),
                ("max_rc", "4"),
            ),
        )
        tasks.append(transport_import)

        # Phase 3: User master import
        user_import = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="PCA User Master Import",
            description=(
                "Import user master records, role assignments, and authorisation profiles. "
                "Validate SAP_ALL/SAP_NEW assignments are removed per security policy."
            ),
            task_type=MigrationTaskType.PCA_USER_MASTER_IMPORT,
            depends_on=(transport_import.id,),
        )
        tasks.append(user_import)

        # Phase 4: Data validation
        data_val = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="Data Validation",
            description=(
                "Execute comprehensive data validation suite — verify configuration "
                "consistency, master data integrity, and system parameter correctness."
            ),
            task_type=MigrationTaskType.DATA_VALIDATION,
            depends_on=(user_import.id,),
        )
        tasks.append(data_val)

        # Phase 5: Final tasks
        final_tasks = self._build_final_tasks(programme_id, depends_on=(data_val.id,))
        tasks.extend(final_tasks)

        return tasks

    # ------------------------------------------------------------------
    # Shared sub-graphs
    # ------------------------------------------------------------------

    def _build_pca_tasks(self, programme_id: str, depends_on: tuple[str, ...]) -> list[MigrationTask]:
        """Post-copy automation task chain."""
        tasks: list[MigrationTask] = []

        client_deletion = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="PCA Client Deletion",
            description=(
                "Delete obsolete clients from target system (SCC5). Remove test/sandbox clients to free resources."
            ),
            task_type=MigrationTaskType.PCA_CLIENT_DELETION,
            depends_on=depends_on,
        )
        tasks.append(client_deletion)

        client_copy = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="PCA Client Copy",
            description=(
                "Execute client copy (SCC9/SCCL) to prepare target client. "
                "Copy customising, cross-client settings, and user master records."
            ),
            task_type=MigrationTaskType.PCA_CLIENT_COPY,
            depends_on=(client_deletion.id,),
            execution_params=(
                ("source_client", "000"),
                ("target_client", "100"),
                ("copy_profile", "SAP_CUST"),
            ),
        )
        tasks.append(client_copy)

        transport_import = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="PCA Transport Import Sequencing",
            description=(
                "Import transport requests in correct dependency order — "
                "customising transports first, then workbench, then ABAP. "
                "Validate import logs for return code <= 4."
            ),
            task_type=MigrationTaskType.PCA_TRANSPORT_IMPORT,
            depends_on=(client_copy.id,),
            execution_params=(
                ("import_mode", "sequential"),
                ("max_rc", "4"),
            ),
        )
        tasks.append(transport_import)

        user_master = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="PCA User Master Import",
            description=(
                "Import user master records, role assignments, and authorisation "
                "profiles. Ensure SAP_ALL/SAP_NEW are stripped per security policy."
            ),
            task_type=MigrationTaskType.PCA_USER_MASTER_IMPORT,
            depends_on=(transport_import.id,),
        )
        tasks.append(user_master)

        return tasks

    def _build_final_tasks(self, programme_id: str, depends_on: tuple[str, ...]) -> list[MigrationTask]:
        """Final health check and manual checkpoint — common to all approaches."""
        tasks: list[MigrationTask] = []

        health_check = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="System Health Check",
            description=(
                "Execute comprehensive system health check — verify all SAP services "
                "are running (SM51), check work process availability (SM66), "
                "validate batch job status (SM37), check RFC destinations (SM59)."
            ),
            task_type=MigrationTaskType.SYSTEM_HEALTH_CHECK,
            depends_on=depends_on,
        )
        tasks.append(health_check)

        checkpoint = _make_task(
            programme_id=programme_id,
            module="migration-orchestrator",
            task_name="Manual Go-Live Checkpoint",
            description=(
                "Manual approval checkpoint — requires sign-off from technical lead, "
                "functional lead, and project manager before proceeding to go-live."
            ),
            task_type=MigrationTaskType.MANUAL_CHECKPOINT,
            depends_on=(health_check.id,),
        )
        tasks.append(checkpoint)

        return tasks

    # ------------------------------------------------------------------
    # Critical path analysis — forward/backward pass algorithm
    # ------------------------------------------------------------------

    def calculate_critical_path(self, tasks: list[MigrationTask]) -> CriticalPathInfo:
        """Compute critical path using proper forward/backward pass algorithm.

        For completed tasks, uses actual duration_minutes.
        For incomplete tasks, uses estimated durations from _DEFAULT_DURATIONS.
        """
        if not tasks:
            return CriticalPathInfo(
                total_duration_minutes=0,
                critical_tasks=(),
                slack_per_task=(),
            )

        task_map: dict[str, MigrationTask] = {t.id: t for t in tasks}
        durations: dict[str, int] = {}
        for t in tasks:
            if t.duration_minutes is not None:
                durations[t.id] = t.duration_minutes
            else:
                durations[t.id] = _DEFAULT_DURATIONS.get(t.task_type, 60)

        # Build adjacency (successors) and reverse adjacency (predecessors)
        successors: dict[str, list[str]] = defaultdict(list)
        predecessors: dict[str, list[str]] = defaultdict(list)
        for t in tasks:
            for dep_id in t.depends_on:
                if dep_id in task_map:
                    successors[dep_id].append(t.id)
                    predecessors[t.id].append(dep_id)

        # Topological sort (Kahn's algorithm)
        in_degree: dict[str, int] = {t.id: 0 for t in tasks}
        for t in tasks:
            for dep_id in t.depends_on:
                if dep_id in task_map:
                    in_degree[t.id] += 1

        queue: list[str] = [tid for tid, deg in in_degree.items() if deg == 0]
        topo_order: list[str] = []
        while queue:
            current = queue.pop(0)
            topo_order.append(current)
            for succ in successors[current]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        # Forward pass — earliest start (ES) and earliest finish (EF)
        es: dict[str, int] = {}
        ef: dict[str, int] = {}
        for tid in topo_order:
            if not predecessors[tid]:
                es[tid] = 0
            else:
                es[tid] = max(ef[p] for p in predecessors[tid])
            ef[tid] = es[tid] + durations[tid]

        # Project total duration
        total_duration = max(ef.values()) if ef else 0

        # Backward pass — latest start (LS) and latest finish (LF)
        lf: dict[str, int] = {}
        ls: dict[str, int] = {}
        for tid in reversed(topo_order):
            if not successors[tid]:
                lf[tid] = total_duration
            else:
                lf[tid] = min(ls[s] for s in successors[tid])
            ls[tid] = lf[tid] - durations[tid]

        # Slack = LS - ES (or equivalently LF - EF)
        slack: dict[str, int] = {tid: ls[tid] - es[tid] for tid in topo_order}

        # Critical path = tasks with zero slack, in topological order
        critical_tasks = tuple(tid for tid in topo_order if slack[tid] == 0)
        slack_per_task = tuple((tid, slack[tid]) for tid in topo_order)

        return CriticalPathInfo(
            total_duration_minutes=total_duration,
            critical_tasks=critical_tasks,
            slack_per_task=slack_per_task,
        )

    # ------------------------------------------------------------------
    # Migration health calculation
    # ------------------------------------------------------------------

    def calculate_migration_health(
        self,
        tasks: list[MigrationTask],
        anomalies: list[AnomalyAlert],
    ) -> MigrationHealth:
        """Compute overall migration health based on task statuses and anomalies."""
        from datetime import datetime, timezone

        completed = sum(1 for t in tasks if t.status == MigrationTaskStatus.COMPLETED)
        in_progress = sum(1 for t in tasks if t.status == MigrationTaskStatus.IN_PROGRESS)
        pending = sum(1 for t in tasks if t.status in (MigrationTaskStatus.PENDING, MigrationTaskStatus.QUEUED))
        failed = sum(1 for t in tasks if t.status == MigrationTaskStatus.FAILED)
        active = sum(1 for a in anomalies if not a.acknowledged)

        # Calculate deviation from critical path
        _critical_path = self.calculate_critical_path(tasks)
        actual_elapsed = 0
        for t in tasks:
            if t.duration_minutes is not None:
                actual_elapsed += t.duration_minutes
        # Simplified deviation — compare actual vs planned for completed tasks
        planned_for_completed = sum(
            _DEFAULT_DURATIONS.get(t.task_type, 60) for t in tasks if t.status == MigrationTaskStatus.COMPLETED
        )
        deviation = actual_elapsed - planned_for_completed if planned_for_completed > 0 else 0

        # Determine overall status
        if failed > 0 or active >= 3:
            overall = "RED"
        elif active > 0 or deviation > 60:
            overall = "AMBER"
        else:
            overall = "GREEN"

        return MigrationHealth(
            overall_status=overall,
            tasks_completed=completed,
            tasks_in_progress=in_progress,
            tasks_pending=pending,
            tasks_failed=failed,
            active_anomalies=active,
            critical_path_deviation_minutes=deviation,
            last_updated=datetime.now(timezone.utc),
        )
