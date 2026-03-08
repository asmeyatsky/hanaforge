"""Tests for TestScenario and TestSuite entities and domain service — pure domain logic, no mocks."""

from datetime import datetime, timezone

import pytest

from domain.entities.test_scenario import TestScenario
from domain.entities.test_suite import TestSuite
from domain.services.test_generation_service import TestGenerationService
from domain.value_objects.test_types import (
    ProcessArea,
    TestPriority,
    TestStatus,
    TestStep,
)


def _make_test_step(*, step_number: int = 1) -> TestStep:
    return TestStep(
        step_number=step_number,
        action=f"Execute step {step_number}",
        expected_result=f"Step {step_number} completes successfully",
        sap_transaction="VA01",
        test_data="Material: MAT-001, Quantity: 10",
    )


def _make_test_scenario(
    *,
    id: str = "ts-001",
    status: TestStatus = TestStatus.DRAFT,
    tags: tuple[str, ...] = ("OTC", "SALES"),
) -> TestScenario:
    return TestScenario(
        id=id,
        programme_id="prog-001",
        process_area=ProcessArea.ORDER_TO_CASH,
        scenario_name="Create Sales Order",
        description="End-to-end test for sales order creation in S/4HANA",
        preconditions=("Customer exists", "Material is available"),
        steps=(_make_test_step(step_number=1), _make_test_step(step_number=2)),
        expected_outcome="Sales order created and saved successfully",
        sap_transaction="VA01",
        fiori_app_id="F0842",
        priority=TestPriority.HIGH,
        status=status,
        tags=tags,
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


def _make_test_suite(
    *,
    scenarios: tuple[str, ...] = ("ts-001", "ts-002"),
    coverage_percentage: float = 0.0,
) -> TestSuite:
    return TestSuite(
        id="suite-001",
        programme_id="prog-001",
        name="OTC Test Suite",
        description="Order-to-Cash end-to-end tests",
        process_area=ProcessArea.ORDER_TO_CASH,
        scenarios=scenarios,
        coverage_percentage=coverage_percentage,
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestCreateTestScenario:
    def test_create_test_scenario(self) -> None:
        scenario = _make_test_scenario()

        assert scenario.id == "ts-001"
        assert scenario.programme_id == "prog-001"
        assert scenario.process_area == ProcessArea.ORDER_TO_CASH
        assert scenario.scenario_name == "Create Sales Order"
        assert scenario.description == "End-to-end test for sales order creation in S/4HANA"
        assert scenario.preconditions == ("Customer exists", "Material is available")
        assert len(scenario.steps) == 2
        assert scenario.steps[0].step_number == 1
        assert scenario.steps[0].sap_transaction == "VA01"
        assert scenario.expected_outcome == "Sales order created and saved successfully"
        assert scenario.sap_transaction == "VA01"
        assert scenario.fiori_app_id == "F0842"
        assert scenario.priority == TestPriority.HIGH
        assert scenario.status == TestStatus.DRAFT
        assert scenario.tags == ("OTC", "SALES")
        assert scenario.domain_events == ()


class TestMarkAsReviewed:
    def test_mark_as_reviewed(self) -> None:
        scenario = _make_test_scenario(status=TestStatus.DRAFT)

        reviewed = scenario.mark_as_reviewed()

        assert reviewed.status == TestStatus.REVIEWED
        # Original unchanged (immutability)
        assert scenario.status == TestStatus.DRAFT

    def test_mark_as_reviewed_rejects_non_draft(self) -> None:
        scenario = _make_test_scenario(status=TestStatus.APPROVED)

        with pytest.raises(ValueError, match="Cannot review scenario"):
            scenario.mark_as_reviewed()


class TestLinkToDefect:
    def test_link_to_defect(self) -> None:
        scenario = _make_test_scenario(tags=("OTC",))

        linked = scenario.link_to_defect("DEF-123")

        assert "defect:DEF-123" in linked.tags
        assert len(linked.tags) == 2
        # Original unchanged
        assert "defect:DEF-123" not in scenario.tags

    def test_link_to_defect_idempotent(self) -> None:
        scenario = _make_test_scenario(tags=("OTC", "defect:DEF-123"))

        linked = scenario.link_to_defect("DEF-123")

        assert linked.tags == scenario.tags


class TestTestSuiteAddScenario:
    def test_test_suite_add_scenario(self) -> None:
        suite = _make_test_suite(scenarios=("ts-001",))

        updated = suite.add_scenario("ts-003")

        assert "ts-003" in updated.scenarios
        assert len(updated.scenarios) == 2
        # Original unchanged
        assert len(suite.scenarios) == 1

    def test_add_scenario_idempotent(self) -> None:
        suite = _make_test_suite(scenarios=("ts-001", "ts-002"))

        updated = suite.add_scenario("ts-001")

        assert updated.scenarios == suite.scenarios


class TestTestSuiteCoverageCalculation:
    def test_test_suite_coverage_calculation(self) -> None:
        suite = _make_test_suite(scenarios=("ts-001", "ts-002", "ts-003"))

        updated = suite.calculate_coverage(total_processes=10)

        assert updated.coverage_percentage == 30.0

    def test_coverage_with_zero_processes(self) -> None:
        suite = _make_test_suite(scenarios=("ts-001",))

        updated = suite.calculate_coverage(total_processes=0)

        assert updated.coverage_percentage == 0.0

    def test_coverage_caps_at_100(self) -> None:
        suite = _make_test_suite(scenarios=("ts-001", "ts-002", "ts-003"))

        updated = suite.calculate_coverage(total_processes=2)

        assert updated.coverage_percentage == 100.0


class TestTraceabilityMatrixGeneration:
    def test_traceability_matrix_generation(self) -> None:
        service = TestGenerationService()

        processes = [
            {"id": "proc-001", "name": "Create Sales Order"},
            {"id": "proc-002", "name": "Post Invoice"},
            {"id": "proc-003", "name": "Goods Receipt"},
        ]

        scenarios = [
            _make_test_scenario(id="ts-001", tags=("OTC",)),
            TestScenario(
                id="ts-002",
                programme_id="prog-001",
                process_area=ProcessArea.PROCURE_TO_PAY,
                scenario_name="Post Invoice",
                description="Test invoice posting in MIRO",
                preconditions=("PO exists",),
                steps=(_make_test_step(),),
                expected_outcome="Invoice posted",
                sap_transaction="MIRO",
                fiori_app_id=None,
                priority=TestPriority.MEDIUM,
                status=TestStatus.DRAFT,
                tags=("P2P",),
                created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        entries = service.build_traceability_matrix(processes, scenarios)

        assert len(entries) >= 3

        # "Create Sales Order" should match scenario ts-001 by name
        create_so = [e for e in entries if e.process_id == "proc-001"]
        assert len(create_so) == 1
        assert create_so[0].coverage_status == "COVERED"
        assert create_so[0].test_scenario_id == "ts-001"

        # "Post Invoice" should match scenario ts-002 by name
        post_inv = [e for e in entries if e.process_id == "proc-002"]
        assert len(post_inv) == 1
        assert post_inv[0].coverage_status == "COVERED"
        assert post_inv[0].test_scenario_id == "ts-002"

        # "Goods Receipt" has no matching scenario
        gr = [e for e in entries if e.process_id == "proc-003"]
        assert len(gr) == 1
        assert gr[0].coverage_status == "NOT_COVERED"
