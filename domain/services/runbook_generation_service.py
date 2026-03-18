"""RunbookGenerationService — pure domain service that generates a structured SAP cutover runbook.

Creates a realistic SAP S/4HANA cutover sequence organised by phase:
  PREPARATION      (T-72h to T-24h) — backups, comms, team briefing
  SYSTEM_LOCKDOWN  (T-24h to T-12h) — user lockout, interface suspension, final backup
  DATA_MIGRATION   (T-12h to T-4h)  — delta loads, reconciliation
  TECHNICAL_CUTOVER(T-4h  to T-1h)  — system conversion, config activation
  VALIDATION       (T-1h  to T+0)   — smoke tests, health checks
  GO_LIVE          (T+0)            — user access, interface activation, comms
  POST_GO_LIVE     (T+0  to T+4h)  — monitoring ramp-up, issue triage
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.entities.cutover_runbook import CutoverRunbook
from domain.value_objects.cutover_types import (
    CutoverCategory,
    CutoverTask,
    GateStatus,
    GateType,
    GoNoGoGate,
    HealthCheck,
    RollbackPlan,
    RunbookStatus,
)


class RunbookGenerationService:
    """Pure domain service — no infrastructure dependencies."""

    def generate_runbook(
        self,
        programme_id: str,
        migration_tasks: list[dict],
        integration_inventory: list[dict],
        data_sequences: list[dict],
    ) -> CutoverRunbook:
        """Generate a complete cutover runbook from programme artefacts."""
        tasks: list[CutoverTask] = []
        order = 0

        # -----------------------------------------------------------------
        # Phase 1: PREPARATION  (T-72h to T-24h)
        # -----------------------------------------------------------------
        prep_tasks = self._generate_preparation_tasks(order)
        tasks.extend(prep_tasks)
        order += len(prep_tasks)

        # -----------------------------------------------------------------
        # Phase 2: SYSTEM_LOCKDOWN  (T-24h to T-12h)
        # -----------------------------------------------------------------
        lockdown_tasks = self._generate_lockdown_tasks(order, integration_inventory, last_prep_id=prep_tasks[-1].id)
        tasks.extend(lockdown_tasks)
        order += len(lockdown_tasks)

        # -----------------------------------------------------------------
        # Phase 3: DATA_MIGRATION  (T-12h to T-4h)
        # -----------------------------------------------------------------
        migration_data_tasks = self._generate_data_migration_tasks(
            order, data_sequences, migration_tasks, last_lockdown_id=lockdown_tasks[-1].id
        )
        tasks.extend(migration_data_tasks)
        order += len(migration_data_tasks)

        # -----------------------------------------------------------------
        # Phase 4: TECHNICAL_CUTOVER  (T-4h to T-1h)
        # -----------------------------------------------------------------
        tech_tasks = self._generate_technical_cutover_tasks(order, last_migration_id=migration_data_tasks[-1].id)
        tasks.extend(tech_tasks)
        order += len(tech_tasks)

        # -----------------------------------------------------------------
        # Phase 5: VALIDATION  (T-1h to T+0)
        # -----------------------------------------------------------------
        validation_tasks = self._generate_validation_tasks(order, last_tech_id=tech_tasks[-1].id)
        tasks.extend(validation_tasks)
        order += len(validation_tasks)

        # -----------------------------------------------------------------
        # Phase 6: GO_LIVE  (T+0)
        # -----------------------------------------------------------------
        golive_tasks = self._generate_go_live_tasks(
            order, integration_inventory, last_validation_id=validation_tasks[-1].id
        )
        tasks.extend(golive_tasks)
        order += len(golive_tasks)

        # -----------------------------------------------------------------
        # Phase 7: POST_GO_LIVE  (T+0 to T+4h)
        # -----------------------------------------------------------------
        post_tasks = self._generate_post_go_live_tasks(order, last_golive_id=golive_tasks[-1].id)
        tasks.extend(post_tasks)

        # -----------------------------------------------------------------
        # Go/No-Go Gates between major phases
        # -----------------------------------------------------------------
        gates = self._generate_gates()

        # -----------------------------------------------------------------
        # Rollback Plan
        # -----------------------------------------------------------------
        rollback = self._generate_rollback_plan(tasks)

        runbook_id = str(uuid.uuid4())
        return CutoverRunbook(
            id=runbook_id,
            programme_id=programme_id,
            version=1,
            name=f"Cutover Runbook v1 — Programme {programme_id[:8]}",
            tasks=tuple(tasks),
            go_nogo_gates=tuple(gates),
            rollback_plan=rollback,
            status=RunbookStatus.DRAFT,
            created_at=datetime.now(timezone.utc),
        )

    # ======================================================================
    # Private helpers — task generation per phase
    # ======================================================================

    def _generate_preparation_tasks(self, start_order: int) -> list[CutoverTask]:
        """T-72h to T-24h: backups, communications, team briefing."""
        base = start_order
        prefix = "PREP"
        return [
            CutoverTask(
                id=f"{prefix}-001",
                name="Send cutover commencement notification to all stakeholders",
                owner="Programme Manager",
                estimated_duration_minutes=15,
                category=CutoverCategory.PREPARATION,
                order=base,
                verification_step="Confirm distribution list delivery receipts",
            ),
            CutoverTask(
                id=f"{prefix}-002",
                name="Verify cutover war-room logistics and communication channels",
                owner="Programme Manager",
                estimated_duration_minutes=30,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.PREPARATION,
                order=base + 1,
                verification_step="Test conference bridge and chat channels",
            ),
            CutoverTask(
                id=f"{prefix}-003",
                name="Execute full production database backup (HANA BACKINT / file backup)",
                owner="Basis Administrator",
                estimated_duration_minutes=120,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.PREPARATION,
                order=base + 2,
                rollback_action="Restore from this backup if cutover fails",
                verification_step="Verify backup catalogue entry and checksum in HANA studio",
            ),
            CutoverTask(
                id=f"{prefix}-004",
                name="Export current SAP transport queue and release all pending transports",
                owner="Basis Administrator",
                estimated_duration_minutes=60,
                depends_on=(f"{prefix}-003",),
                category=CutoverCategory.PREPARATION,
                order=base + 3,
                verification_step="STMS queue shows zero unreleased transports",
            ),
            CutoverTask(
                id=f"{prefix}-005",
                name="Conduct cutover team briefing and role assignment confirmation",
                owner="Programme Manager",
                estimated_duration_minutes=60,
                depends_on=(f"{prefix}-002",),
                category=CutoverCategory.PREPARATION,
                order=base + 4,
                verification_step="All team members confirm readiness in sign-off sheet",
            ),
            CutoverTask(
                id=f"{prefix}-006",
                name="Validate DR/failover procedures and escalation matrix",
                owner="Infrastructure Lead",
                estimated_duration_minutes=45,
                depends_on=(f"{prefix}-005",),
                category=CutoverCategory.PREPARATION,
                order=base + 5,
                verification_step="DR runbook reviewed and escalation contacts verified",
            ),
            CutoverTask(
                id=f"{prefix}-007",
                name="Freeze change management — no new transports or config changes",
                owner="Change Manager",
                estimated_duration_minutes=15,
                depends_on=(f"{prefix}-004",),
                category=CutoverCategory.PREPARATION,
                order=base + 6,
                verification_step="Change freeze notification sent and STMS locked",
            ),
        ]

    def _generate_lockdown_tasks(
        self,
        start_order: int,
        integration_inventory: list[dict],
        last_prep_id: str,
    ) -> list[CutoverTask]:
        """T-24h to T-12h: user lockout, interface suspension, final backup."""
        base = start_order
        prefix = "LOCK"
        tasks = [
            CutoverTask(
                id=f"{prefix}-001",
                name="Lock all end-user access in production (SU01 mass lock)",
                owner="Security Administrator",
                estimated_duration_minutes=30,
                depends_on=(last_prep_id,),
                category=CutoverCategory.SYSTEM_LOCKDOWN,
                order=base,
                rollback_action="Mass unlock user accounts via SU01",
                verification_step="SM04 shows zero active user sessions",
            ),
            CutoverTask(
                id=f"{prefix}-002",
                name="Suspend all batch job scheduling (SM36/SM37 hold)",
                owner="Basis Administrator",
                estimated_duration_minutes=15,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.SYSTEM_LOCKDOWN,
                order=base + 1,
                rollback_action="Release batch job scheduling",
                verification_step="SM37 confirms no active or scheduled jobs",
            ),
            CutoverTask(
                id=f"{prefix}-003",
                name="Deactivate all inbound/outbound interfaces and RFC connections",
                owner="Integration Lead",
                estimated_duration_minutes=45,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.SYSTEM_LOCKDOWN,
                order=base + 2,
                rollback_action="Reactivate interfaces using saved configuration",
                verification_step="SM59 RFC destinations disabled; IDoc processing stopped (WE19)",
            ),
        ]

        # Add per-interface deactivation tasks from inventory
        for idx, iface in enumerate(integration_inventory[:5]):
            iface_name = iface.get("name", f"Interface-{idx + 1}")
            tasks.append(
                CutoverTask(
                    id=f"{prefix}-IF-{idx + 1:03d}",
                    name=f"Verify deactivation of interface: {iface_name}",
                    owner="Integration Lead",
                    estimated_duration_minutes=10,
                    depends_on=(f"{prefix}-003",),
                    category=CutoverCategory.SYSTEM_LOCKDOWN,
                    order=base + 3 + idx,
                    verification_step=f"Confirm {iface_name} shows no active connections",
                )
            )

        final_order = base + 3 + len(integration_inventory[:5])
        last_lockdown_dep = tasks[-1].id

        tasks.extend(
            [
                CutoverTask(
                    id=f"{prefix}-004",
                    name="Execute pre-cutover final HANA database backup (point-in-time)",
                    owner="Basis Administrator",
                    estimated_duration_minutes=90,
                    depends_on=(last_lockdown_dep,),
                    category=CutoverCategory.SYSTEM_LOCKDOWN,
                    order=final_order,
                    rollback_action="Restore from this point-in-time backup",
                    verification_step="Backup catalogue timestamp verified in HANA studio",
                ),
                CutoverTask(
                    id=f"{prefix}-005",
                    name="Snapshot application server file systems and config",
                    owner="Infrastructure Lead",
                    estimated_duration_minutes=30,
                    depends_on=(last_lockdown_dep,),
                    category=CutoverCategory.SYSTEM_LOCKDOWN,
                    order=final_order + 1,
                    rollback_action="Restore file system snapshots",
                    verification_step="Snapshot IDs recorded and verified",
                ),
            ]
        )
        return tasks

    def _generate_data_migration_tasks(
        self,
        start_order: int,
        data_sequences: list[dict],
        migration_tasks: list[dict],
        last_lockdown_id: str,
    ) -> list[CutoverTask]:
        """T-12h to T-4h: delta loads, data reconciliation."""
        base = start_order
        prefix = "DATA"
        tasks = [
            CutoverTask(
                id=f"{prefix}-001",
                name="Execute delta data extraction from legacy system",
                owner="Data Migration Lead",
                estimated_duration_minutes=120,
                depends_on=(last_lockdown_id,),
                category=CutoverCategory.DATA_MIGRATION,
                order=base,
                rollback_action="Reverse delta load using saved rollback scripts",
                verification_step="Extraction log shows zero errors; row counts match",
            ),
        ]

        # Generate tasks from data_sequences
        for idx, seq in enumerate(data_sequences[:8]):
            seq_name = seq.get("name", f"Data-Sequence-{idx + 1}")
            est_duration = seq.get("estimated_minutes", 60)
            tasks.append(
                CutoverTask(
                    id=f"{prefix}-SEQ-{idx + 1:03d}",
                    name=f"Load data sequence: {seq_name}",
                    owner="Data Migration Lead",
                    estimated_duration_minutes=est_duration,
                    depends_on=(f"{prefix}-001",),
                    category=CutoverCategory.DATA_MIGRATION,
                    order=base + 1 + idx,
                    rollback_action=f"Reverse {seq_name} via rollback script",
                    verification_step=f"Record count and checksum validation for {seq_name}",
                )
            )

        # Generate tasks from migration_tasks provided by the caller
        seq_offset = 1 + len(data_sequences[:8])
        for idx, mtask in enumerate(migration_tasks[:5]):
            task_name = mtask.get("name", f"Migration-Task-{idx + 1}")
            est = mtask.get("estimated_minutes", 45)
            tasks.append(
                CutoverTask(
                    id=f"{prefix}-MIG-{idx + 1:03d}",
                    name=f"Execute migration task: {task_name}",
                    owner="Data Migration Lead",
                    estimated_duration_minutes=est,
                    depends_on=(f"{prefix}-001",),
                    category=CutoverCategory.DATA_MIGRATION,
                    order=base + seq_offset + idx,
                    rollback_action=f"Revert {task_name}",
                    verification_step=f"Post-load validation for {task_name}",
                )
            )

        last_data_dep = tasks[-1].id
        recon_order = base + seq_offset + len(migration_tasks[:5])
        tasks.extend(
            [
                CutoverTask(
                    id=f"{prefix}-RECON-001",
                    name="Run data reconciliation — record counts source vs target",
                    owner="Data Migration Lead",
                    estimated_duration_minutes=60,
                    depends_on=(last_data_dep,),
                    category=CutoverCategory.DATA_MIGRATION,
                    order=recon_order,
                    verification_step="Reconciliation report shows <0.01% variance",
                ),
                CutoverTask(
                    id=f"{prefix}-RECON-002",
                    name="Run data reconciliation — checksum and hash validation",
                    owner="Data Migration Lead",
                    estimated_duration_minutes=45,
                    depends_on=(last_data_dep,),
                    category=CutoverCategory.DATA_MIGRATION,
                    order=recon_order + 1,
                    verification_step="All checksums match between source and HANA target",
                ),
                CutoverTask(
                    id=f"{prefix}-RECON-003",
                    name="Run financial data reconciliation (FI/CO balances)",
                    owner="Finance Lead",
                    estimated_duration_minutes=60,
                    depends_on=(f"{prefix}-RECON-001",),
                    category=CutoverCategory.DATA_MIGRATION,
                    order=recon_order + 2,
                    verification_step="Trial balance matches source system to the cent",
                ),
            ]
        )
        return tasks

    def _generate_technical_cutover_tasks(self, start_order: int, last_migration_id: str) -> list[CutoverTask]:
        """T-4h to T-1h: system conversion, config activation."""
        base = start_order
        prefix = "TECH"
        return [
            CutoverTask(
                id=f"{prefix}-001",
                name="Execute S/4HANA system conversion (SUM/DMO)",
                owner="Basis Administrator",
                estimated_duration_minutes=90,
                depends_on=(last_migration_id,),
                category=CutoverCategory.TECHNICAL_CUTOVER,
                order=base,
                rollback_action="Restore pre-conversion HANA backup",
                verification_step="SUM tool shows conversion completed without errors",
            ),
            CutoverTask(
                id=f"{prefix}-002",
                name="Activate S/4HANA business functions and Fiori apps",
                owner="Functional Lead",
                estimated_duration_minutes=30,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.TECHNICAL_CUTOVER,
                order=base + 1,
                verification_step="SFW5 shows all target business functions active",
            ),
            CutoverTask(
                id=f"{prefix}-003",
                name="Apply custom code remediation transports",
                owner="Development Lead",
                estimated_duration_minutes=45,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.TECHNICAL_CUTOVER,
                order=base + 2,
                rollback_action="Reverse transport via STMS",
                verification_step="Transport log shows RC=0 for all requests",
            ),
            CutoverTask(
                id=f"{prefix}-004",
                name="Configure output management and print queues",
                owner="Basis Administrator",
                estimated_duration_minutes=20,
                depends_on=(f"{prefix}-002",),
                category=CutoverCategory.TECHNICAL_CUTOVER,
                order=base + 3,
                verification_step="SPAD shows all printers online and test page printed",
            ),
            CutoverTask(
                id=f"{prefix}-005",
                name="Update number ranges and fiscal year settings",
                owner="Functional Lead",
                estimated_duration_minutes=30,
                depends_on=(f"{prefix}-002",),
                category=CutoverCategory.TECHNICAL_CUTOVER,
                order=base + 4,
                verification_step="SNRO number ranges verified; OB29 fiscal year confirmed",
            ),
            CutoverTask(
                id=f"{prefix}-006",
                name="Execute HANA post-conversion optimisation (statistics, indexes)",
                owner="Basis Administrator",
                estimated_duration_minutes=45,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.TECHNICAL_CUTOVER,
                order=base + 5,
                verification_step="HANA Administration Console shows healthy index status",
            ),
        ]

    def _generate_validation_tasks(self, start_order: int, last_tech_id: str) -> list[CutoverTask]:
        """T-1h to T+0: smoke tests, health checks."""
        base = start_order
        prefix = "VAL"
        return [
            CutoverTask(
                id=f"{prefix}-001",
                name="Run automated smoke test suite (critical business processes)",
                owner="QA Lead",
                estimated_duration_minutes=30,
                depends_on=(last_tech_id,),
                category=CutoverCategory.VALIDATION,
                order=base,
                verification_step="All smoke test scenarios pass (green)",
            ),
            CutoverTask(
                id=f"{prefix}-002",
                name="Validate Fiori launchpad accessibility and role assignments",
                owner="Security Administrator",
                estimated_duration_minutes=15,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.VALIDATION,
                order=base + 1,
                verification_step="Test users can access assigned Fiori tiles",
            ),
            CutoverTask(
                id=f"{prefix}-003",
                name="Execute HANA system health check (memory, CPU, disk, alerts)",
                owner="Basis Administrator",
                estimated_duration_minutes=15,
                depends_on=(last_tech_id,),
                category=CutoverCategory.VALIDATION,
                order=base + 2,
                verification_step="HANA health dashboard shows all green indicators",
            ),
            CutoverTask(
                id=f"{prefix}-004",
                name="Validate RFC destination connectivity (SM59 test)",
                owner="Integration Lead",
                estimated_duration_minutes=20,
                depends_on=(last_tech_id,),
                category=CutoverCategory.VALIDATION,
                order=base + 3,
                verification_step="All RFC destinations return successful ping",
            ),
            CutoverTask(
                id=f"{prefix}-005",
                name="Run SAP EarlyWatch / Solution Manager checks",
                owner="Basis Administrator",
                estimated_duration_minutes=20,
                depends_on=(f"{prefix}-003",),
                category=CutoverCategory.VALIDATION,
                order=base + 4,
                verification_step="No red alerts in Solution Manager dashboard",
            ),
            CutoverTask(
                id=f"{prefix}-006",
                name="Business process owner sign-off on critical transactions",
                owner="Business Process Owner",
                estimated_duration_minutes=30,
                depends_on=(f"{prefix}-001", f"{prefix}-002"),
                category=CutoverCategory.VALIDATION,
                order=base + 5,
                verification_step="Sign-off received from all process owners",
            ),
        ]

    def _generate_go_live_tasks(
        self,
        start_order: int,
        integration_inventory: list[dict],
        last_validation_id: str,
    ) -> list[CutoverTask]:
        """T+0: user access, interface activation, communications."""
        base = start_order
        prefix = "LIVE"
        tasks = [
            CutoverTask(
                id=f"{prefix}-001",
                name="Unlock end-user access in production (SU01 mass unlock)",
                owner="Security Administrator",
                estimated_duration_minutes=15,
                depends_on=(last_validation_id,),
                category=CutoverCategory.GO_LIVE,
                order=base,
                verification_step="SM04 shows users logging in; SUIM confirms unlock",
            ),
            CutoverTask(
                id=f"{prefix}-002",
                name="Reactivate all inbound/outbound interfaces and IDocs",
                owner="Integration Lead",
                estimated_duration_minutes=30,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.GO_LIVE,
                order=base + 1,
                verification_step="SM59 RFC destinations active; WE19 IDoc processing resumed",
            ),
            CutoverTask(
                id=f"{prefix}-003",
                name="Release batch job scheduling (SM36)",
                owner="Basis Administrator",
                estimated_duration_minutes=10,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.GO_LIVE,
                order=base + 2,
                verification_step="SM37 shows scheduled jobs running on time",
            ),
            CutoverTask(
                id=f"{prefix}-004",
                name="Send go-live announcement to all business users",
                owner="Programme Manager",
                estimated_duration_minutes=10,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.GO_LIVE,
                order=base + 3,
                verification_step="Communication distribution confirmed",
            ),
            CutoverTask(
                id=f"{prefix}-005",
                name="Activate help desk and floor-walker support teams",
                owner="Support Lead",
                estimated_duration_minutes=15,
                depends_on=(f"{prefix}-004",),
                category=CutoverCategory.GO_LIVE,
                order=base + 4,
                verification_step="Support teams online and ticket queue active",
            ),
        ]
        return tasks

    def _generate_post_go_live_tasks(self, start_order: int, last_golive_id: str) -> list[CutoverTask]:
        """T+0 to T+4h: monitoring ramp-up, issue triage."""
        base = start_order
        prefix = "POST"
        return [
            CutoverTask(
                id=f"{prefix}-001",
                name="Activate enhanced monitoring (HANA alerts, app-server health)",
                owner="Basis Administrator",
                estimated_duration_minutes=15,
                depends_on=(last_golive_id,),
                category=CutoverCategory.POST_GO_LIVE,
                order=base,
                verification_step="Monitoring dashboards live and alerts configured",
            ),
            CutoverTask(
                id=f"{prefix}-002",
                name="Monitor first batch job cycle completion",
                owner="Basis Administrator",
                estimated_duration_minutes=60,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.POST_GO_LIVE,
                order=base + 1,
                verification_step="SM37 shows first cycle jobs completed successfully",
            ),
            CutoverTask(
                id=f"{prefix}-003",
                name="Monitor interface message flow and IDoc processing",
                owner="Integration Lead",
                estimated_duration_minutes=60,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.POST_GO_LIVE,
                order=base + 2,
                verification_step="BD87 shows IDocs processed; no stuck messages",
            ),
            CutoverTask(
                id=f"{prefix}-004",
                name="Triage and categorise early user-reported issues",
                owner="Support Lead",
                estimated_duration_minutes=120,
                depends_on=(f"{prefix}-001",),
                category=CutoverCategory.POST_GO_LIVE,
                order=base + 3,
                verification_step="Issue log reviewed; critical issues escalated",
            ),
            CutoverTask(
                id=f"{prefix}-005",
                name="Conduct T+4h cutover status review meeting",
                owner="Programme Manager",
                estimated_duration_minutes=30,
                depends_on=(f"{prefix}-002", f"{prefix}-003", f"{prefix}-004"),
                category=CutoverCategory.POST_GO_LIVE,
                order=base + 4,
                verification_step="Status review documented; next actions agreed",
            ),
        ]

    # ======================================================================
    # Go/No-Go Gates
    # ======================================================================

    def _generate_gates(self) -> list[GoNoGoGate]:
        """Create go/no-go decision gates between major cutover phases."""
        return [
            GoNoGoGate(
                id="GATE-PRE-LOCKDOWN",
                name="Pre-Lockdown Readiness Gate",
                gate_type=GateType.BUSINESS_SIGN_OFF,
                checks=(
                    HealthCheck(
                        name="Team readiness confirmed",
                        check_type="manual",
                        target_value="ALL_CONFIRMED",
                    ),
                    HealthCheck(
                        name="Backup completed successfully",
                        check_type="system",
                        target_value="BACKUP_COMPLETE",
                    ),
                    HealthCheck(
                        name="Change freeze in effect",
                        check_type="system",
                        target_value="FREEZE_ACTIVE",
                    ),
                ),
                required_approval=True,
                status=GateStatus.NOT_EVALUATED,
            ),
            GoNoGoGate(
                id="GATE-PRE-MIGRATION",
                name="Pre-Data-Migration Gate",
                gate_type=GateType.SYSTEM_HEALTH,
                checks=(
                    HealthCheck(
                        name="HANA database availability",
                        check_type="hana_ping",
                        target_value="AVAILABLE",
                    ),
                    HealthCheck(
                        name="Application server status",
                        check_type="app_server",
                        target_value="RUNNING",
                    ),
                    HealthCheck(
                        name="All users locked out",
                        check_type="user_sessions",
                        target_value="ZERO_SESSIONS",
                    ),
                    HealthCheck(
                        name="Interfaces deactivated",
                        check_type="interface_status",
                        target_value="ALL_SUSPENDED",
                    ),
                ),
                required_approval=True,
                status=GateStatus.NOT_EVALUATED,
            ),
            GoNoGoGate(
                id="GATE-PRE-CONVERSION",
                name="Pre-Technical-Conversion Gate",
                gate_type=GateType.DATA_RECONCILIATION,
                checks=(
                    HealthCheck(
                        name="Record count reconciliation",
                        check_type="data_recon",
                        target_value="COUNTS_MATCH",
                    ),
                    HealthCheck(
                        name="Checksum validation",
                        check_type="data_recon",
                        target_value="CHECKSUMS_MATCH",
                    ),
                    HealthCheck(
                        name="Financial balance reconciliation",
                        check_type="data_recon",
                        target_value="BALANCES_MATCH",
                    ),
                ),
                required_approval=True,
                status=GateStatus.NOT_EVALUATED,
            ),
            GoNoGoGate(
                id="GATE-PRE-GOLIVE",
                name="Final Go/No-Go Gate",
                gate_type=GateType.FINAL_GO_LIVE,
                checks=(
                    HealthCheck(
                        name="HANA system health",
                        check_type="hana_health",
                        target_value="HEALTHY",
                    ),
                    HealthCheck(
                        name="Smoke tests passed",
                        check_type="test_results",
                        target_value="ALL_PASSED",
                    ),
                    HealthCheck(
                        name="RFC connectivity verified",
                        check_type="rfc_test",
                        target_value="ALL_CONNECTED",
                    ),
                    HealthCheck(
                        name="Business process owner sign-off",
                        check_type="manual",
                        target_value="ALL_SIGNED_OFF",
                    ),
                    HealthCheck(
                        name="Performance baseline within threshold",
                        check_type="performance",
                        target_value="WITHIN_THRESHOLD",
                    ),
                ),
                required_approval=True,
                status=GateStatus.NOT_EVALUATED,
            ),
            GoNoGoGate(
                id="GATE-INTERFACE-REACTIVATION",
                name="Interface Reactivation Gate",
                gate_type=GateType.INTERFACE_CONNECTIVITY,
                checks=(
                    HealthCheck(
                        name="RFC destinations reachable",
                        check_type="rfc_test",
                        target_value="ALL_CONNECTED",
                    ),
                    HealthCheck(
                        name="IDoc processing functional",
                        check_type="idoc_test",
                        target_value="PROCESSING_OK",
                    ),
                    HealthCheck(
                        name="API endpoints responding",
                        check_type="api_health",
                        target_value="ALL_HEALTHY",
                    ),
                ),
                required_approval=False,
                status=GateStatus.NOT_EVALUATED,
            ),
            GoNoGoGate(
                id="GATE-PERFORMANCE",
                name="Performance Baseline Gate",
                gate_type=GateType.PERFORMANCE_BASELINE,
                checks=(
                    HealthCheck(
                        name="Dialog response time < 1s",
                        check_type="response_time",
                        target_value="<1000ms",
                    ),
                    HealthCheck(
                        name="Batch throughput within range",
                        check_type="batch_throughput",
                        target_value=">=80%_BASELINE",
                    ),
                    HealthCheck(
                        name="HANA memory utilisation < 80%",
                        check_type="hana_memory",
                        target_value="<80%",
                    ),
                ),
                required_approval=False,
                status=GateStatus.NOT_EVALUATED,
            ),
        ]

    # ======================================================================
    # Rollback Plan
    # ======================================================================

    def _generate_rollback_plan(self, tasks: list[CutoverTask]) -> RollbackPlan:
        """Generate a rollback plan based on the task list."""
        # Point of no return is the start of technical conversion
        ponr_id: str | None = None
        for t in tasks:
            if t.category == CutoverCategory.TECHNICAL_CUTOVER:
                ponr_id = t.id
                break

        return RollbackPlan(
            trigger_conditions=(
                "Critical go/no-go gate failure with no override approval",
                "Data reconciliation variance exceeds 0.1%",
                "HANA system becomes unavailable during migration",
                "Multiple critical interface failures post-activation",
                "Business process owner refuses sign-off",
            ),
            rollback_steps=(
                "1. Halt all running cutover tasks immediately",
                "2. Notify all stakeholders of rollback decision",
                "3. Reactivate legacy system interfaces",
                "4. Restore HANA database from pre-cutover backup",
                "5. Restore application server file system snapshots",
                "6. Unlock user accounts on legacy system",
                "7. Release batch job scheduling on legacy system",
                "8. Verify legacy system operational (smoke tests)",
                "9. Send rollback communication to business users",
                "10. Conduct post-rollback review meeting",
            ),
            max_rollback_window_hours=8,
            point_of_no_return_task_id=ponr_id,
        )
