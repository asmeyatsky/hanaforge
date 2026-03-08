"""Tests for RunbookGenerationService — pure domain logic, no mocks."""

from domain.services.runbook_generation_service import RunbookGenerationService
from domain.value_objects.cutover_types import (
    CutoverCategory,
    GateStatus,
    GateType,
    RunbookStatus,
)


def _make_service() -> RunbookGenerationService:
    return RunbookGenerationService()


def _sample_artefacts() -> tuple[list[dict], list[dict], list[dict]]:
    migration_tasks = [
        {"name": "Migrate vendor master data", "estimated_minutes": 60},
        {"name": "Migrate customer open items", "estimated_minutes": 90},
    ]
    integration_inventory = [
        {"name": "SAP-PI-ORDERS", "type": "RFC"},
        {"name": "EDI-INVOICES", "type": "IDoc"},
        {"name": "CRM-API", "type": "REST"},
    ]
    data_sequences = [
        {"name": "GL Account Balances", "estimated_minutes": 120},
        {"name": "Material Master", "estimated_minutes": 90},
        {"name": "Customer Master", "estimated_minutes": 60},
    ]
    return migration_tasks, integration_inventory, data_sequences


class TestGenerateRunbook:
    def test_generate_runbook_has_all_categories(self) -> None:
        service = _make_service()
        migration_tasks, integration_inventory, data_sequences = _sample_artefacts()

        runbook = service.generate_runbook(
            programme_id="prog-001",
            migration_tasks=migration_tasks,
            integration_inventory=integration_inventory,
            data_sequences=data_sequences,
        )

        categories_present = {t.category for t in runbook.tasks}
        expected_categories = {
            CutoverCategory.PREPARATION,
            CutoverCategory.SYSTEM_LOCKDOWN,
            CutoverCategory.DATA_MIGRATION,
            CutoverCategory.TECHNICAL_CUTOVER,
            CutoverCategory.VALIDATION,
            CutoverCategory.GO_LIVE,
            CutoverCategory.POST_GO_LIVE,
        }
        assert expected_categories.issubset(categories_present), (
            f"Missing categories: {expected_categories - categories_present}"
        )

    def test_runbook_tasks_ordered_by_category(self) -> None:
        service = _make_service()
        migration_tasks, integration_inventory, data_sequences = _sample_artefacts()

        runbook = service.generate_runbook(
            programme_id="prog-001",
            migration_tasks=migration_tasks,
            integration_inventory=integration_inventory,
            data_sequences=data_sequences,
        )

        # Tasks should be in increasing order
        orders = [t.order for t in runbook.tasks]
        assert orders == sorted(orders), "Tasks should be ordered by their order field"

        # Category ordering should follow the cutover sequence
        category_order = [
            CutoverCategory.PREPARATION,
            CutoverCategory.SYSTEM_LOCKDOWN,
            CutoverCategory.DATA_MIGRATION,
            CutoverCategory.TECHNICAL_CUTOVER,
            CutoverCategory.VALIDATION,
            CutoverCategory.GO_LIVE,
            CutoverCategory.POST_GO_LIVE,
        ]
        seen_categories: list[CutoverCategory] = []
        for task in runbook.tasks:
            if not seen_categories or task.category != seen_categories[-1]:
                seen_categories.append(task.category)

        for i, cat in enumerate(seen_categories):
            assert cat in category_order, f"Unexpected category: {cat}"
            if i > 0:
                prev_idx = category_order.index(seen_categories[i - 1])
                curr_idx = category_order.index(cat)
                assert curr_idx >= prev_idx, (
                    f"Category {cat} appeared after {seen_categories[i-1]} "
                    f"but should not precede it in execution order"
                )

    def test_runbook_includes_go_nogo_gates(self) -> None:
        service = _make_service()
        migration_tasks, integration_inventory, data_sequences = _sample_artefacts()

        runbook = service.generate_runbook(
            programme_id="prog-001",
            migration_tasks=migration_tasks,
            integration_inventory=integration_inventory,
            data_sequences=data_sequences,
        )

        assert len(runbook.go_nogo_gates) >= 4, (
            "Should have at least 4 gates between major phases"
        )

        gate_types_present = {g.gate_type for g in runbook.go_nogo_gates}
        assert GateType.SYSTEM_HEALTH in gate_types_present
        assert GateType.DATA_RECONCILIATION in gate_types_present
        assert GateType.FINAL_GO_LIVE in gate_types_present
        assert GateType.INTERFACE_CONNECTIVITY in gate_types_present

        # All gates should start as NOT_EVALUATED
        for gate in runbook.go_nogo_gates:
            assert gate.status == GateStatus.NOT_EVALUATED

        # Each gate should have checks
        for gate in runbook.go_nogo_gates:
            assert len(gate.checks) > 0, f"Gate {gate.name} has no checks"

    def test_runbook_includes_rollback_plan(self) -> None:
        service = _make_service()
        migration_tasks, integration_inventory, data_sequences = _sample_artefacts()

        runbook = service.generate_runbook(
            programme_id="prog-001",
            migration_tasks=migration_tasks,
            integration_inventory=integration_inventory,
            data_sequences=data_sequences,
        )

        rp = runbook.rollback_plan
        assert len(rp.trigger_conditions) > 0, "Rollback plan should have trigger conditions"
        assert len(rp.rollback_steps) > 0, "Rollback plan should have steps"
        assert rp.max_rollback_window_hours > 0
        assert rp.point_of_no_return_task_id is not None, (
            "Should identify point of no return"
        )

        # Point of no return should be a TECHNICAL_CUTOVER task
        ponr_task = next(
            (t for t in runbook.tasks if t.id == rp.point_of_no_return_task_id),
            None,
        )
        assert ponr_task is not None, "Point of no return task should exist"
        assert ponr_task.category == CutoverCategory.TECHNICAL_CUTOVER


class TestApproveRunbook:
    def test_approve_runbook(self) -> None:
        service = _make_service()
        migration_tasks, integration_inventory, data_sequences = _sample_artefacts()

        runbook = service.generate_runbook(
            programme_id="prog-001",
            migration_tasks=migration_tasks,
            integration_inventory=integration_inventory,
            data_sequences=data_sequences,
        )
        assert runbook.status == RunbookStatus.DRAFT

        approved = runbook.approve("john.smith@acme.com")

        assert approved.status == RunbookStatus.APPROVED
        assert approved.approved_by == "john.smith@acme.com"
        assert approved.approved_at is not None
        # Original unchanged
        assert runbook.status == RunbookStatus.DRAFT

    def test_cannot_approve_already_approved(self) -> None:
        service = _make_service()
        migration_tasks, integration_inventory, data_sequences = _sample_artefacts()

        runbook = service.generate_runbook(
            programme_id="prog-001",
            migration_tasks=migration_tasks,
            integration_inventory=integration_inventory,
            data_sequences=data_sequences,
        )
        approved = runbook.approve("john.smith@acme.com")

        import pytest

        with pytest.raises(ValueError, match="Cannot approve"):
            approved.approve("another.approver@acme.com")


class TestRunbookEdgeCases:
    def test_generate_with_empty_artefacts(self) -> None:
        """Runbook generation should work even with empty input."""
        service = _make_service()
        runbook = service.generate_runbook(
            programme_id="prog-002",
            migration_tasks=[],
            integration_inventory=[],
            data_sequences=[],
        )
        assert len(runbook.tasks) > 0, "Should still generate base tasks"
        assert runbook.status == RunbookStatus.DRAFT

    def test_tasks_have_owners(self) -> None:
        """Every task should have an assigned owner."""
        service = _make_service()
        migration_tasks, integration_inventory, data_sequences = _sample_artefacts()

        runbook = service.generate_runbook(
            programme_id="prog-001",
            migration_tasks=migration_tasks,
            integration_inventory=integration_inventory,
            data_sequences=data_sequences,
        )
        for task in runbook.tasks:
            assert task.owner, f"Task {task.id} has no owner"

    def test_data_sequence_tasks_from_artefacts(self) -> None:
        """Data migration tasks should incorporate provided data sequences."""
        service = _make_service()
        data_sequences = [
            {"name": "GL Balances", "estimated_minutes": 120},
            {"name": "AP Open Items", "estimated_minutes": 90},
        ]

        runbook = service.generate_runbook(
            programme_id="prog-001",
            migration_tasks=[],
            integration_inventory=[],
            data_sequences=data_sequences,
        )

        data_tasks = [
            t for t in runbook.tasks if t.category == CutoverCategory.DATA_MIGRATION
        ]
        task_names = " ".join(t.name for t in data_tasks)
        assert "GL Balances" in task_names
        assert "AP Open Items" in task_names
