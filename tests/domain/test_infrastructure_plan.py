"""Tests for InfrastructurePlan aggregate root — pure domain logic, no mocks."""

from datetime import datetime, timezone

import pytest

from domain.entities.infrastructure_plan import InfrastructurePlan
from domain.events.infrastructure_events import (
    InfrastructurePlanCreatedEvent,
    PlanValidatedEvent,
    TerraformPlanGeneratedEvent,
)
from domain.value_objects.gcp_types import (
    AppServerConfig,
    CostEstimate,
    GCPMachineType,
    HANAConfig,
    NetworkConfig,
    SecurityConfig,
    ValidationResult,
    ValidationStatus,
)


def _make_plan(
    *,
    ha_enabled: bool = True,
    validation_status: ValidationStatus = ValidationStatus.NOT_VALIDATED,
    terraform_ref: str | None = None,
) -> InfrastructurePlan:
    """Factory for test InfrastructurePlan instances."""
    return InfrastructurePlan(
        id="plan-001",
        programme_id="prog-001",
        region="us-central1",
        dr_region="us-east4",
        hana_config=HANAConfig(
            instance_type=GCPMachineType.M3_ULTRAMEM_64,
            memory_gb=1792,
            hana_data_disk_gb=750,
            hana_log_disk_gb=512,
            hana_shared_disk_gb=1024,
            backup_disk_gb=1000,
        ),
        app_server_config=AppServerConfig(
            instance_type=GCPMachineType.C3_STANDARD_22,
            instance_count=2,
            auto_scaling=True,
            min_instances=2,
            max_instances=6,
        ),
        network_config=NetworkConfig(
            vpc_name="sap-vpc-prog001",
            subnet_cidr_db="10.0.1.0/24",
            subnet_cidr_app="10.0.2.0/24",
            subnet_cidr_web="10.0.3.0/24",
            enable_cloud_nat=True,
            enable_private_google_access=True,
            interconnect_bandwidth_gbps=None,
        ),
        ha_enabled=ha_enabled,
        dr_enabled=True,
        security_config=SecurityConfig(
            enable_cmek=True,
            enable_vpc_sc=True,
            enable_os_login=True,
            enable_binary_auth=True,
            kms_key_ring="sap-kms-prog001",
        ),
        estimated_monthly_cost=CostEstimate(
            hana_monthly=27_340.00,
            app_server_monthly=1_672.00,
            storage_monthly=350.00,
            network_monthly=220.00,
            backup_monthly=10.00,
            monitoring_monthly=56.00,
            cud_discount_percentage=37.0,
        ),
        terraform_plan_ref=terraform_ref,
        validation_status=validation_status,
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestCreatePlan:
    def test_create_plan_via_factory(self) -> None:
        plan = InfrastructurePlan.create(
            id="plan-002",
            programme_id="prog-002",
            region="europe-west3",
            dr_region="europe-west1",
            hana_config=HANAConfig(
                instance_type=GCPMachineType.M3_ULTRAMEM_32,
                memory_gb=896,
                hana_data_disk_gb=750,
                hana_log_disk_gb=512,
                hana_shared_disk_gb=1024,
                backup_disk_gb=1000,
            ),
            app_server_config=AppServerConfig(
                instance_type=GCPMachineType.C3_STANDARD_8,
                instance_count=1,
                auto_scaling=False,
                min_instances=1,
                max_instances=1,
            ),
            network_config=NetworkConfig(
                vpc_name="sap-vpc-dev",
                subnet_cidr_db="10.0.1.0/24",
                subnet_cidr_app="10.0.2.0/24",
                subnet_cidr_web="10.0.3.0/24",
                enable_cloud_nat=True,
                enable_private_google_access=True,
                interconnect_bandwidth_gbps=None,
            ),
            ha_enabled=False,
            dr_enabled=False,
            security_config=SecurityConfig(
                enable_cmek=False,
                enable_vpc_sc=False,
                enable_os_login=True,
                enable_binary_auth=False,
                kms_key_ring=None,
            ),
            estimated_monthly_cost=CostEstimate(
                hana_monthly=6_835.00,
                app_server_monthly=304.00,
                storage_monthly=200.00,
                network_monthly=100.00,
                backup_monthly=5.00,
                monitoring_monthly=24.00,
                cud_discount_percentage=20.0,
            ),
        )

        assert plan.id == "plan-002"
        assert plan.programme_id == "prog-002"
        assert plan.region == "europe-west3"
        assert plan.validation_status == ValidationStatus.NOT_VALIDATED
        assert plan.terraform_plan_ref is None
        assert len(plan.domain_events) == 1
        assert isinstance(plan.domain_events[0], InfrastructurePlanCreatedEvent)
        assert plan.domain_events[0].programme_id == "prog-002"

    def test_create_plan_direct(self) -> None:
        plan = _make_plan()

        assert plan.id == "plan-001"
        assert plan.hana_config.instance_type == GCPMachineType.M3_ULTRAMEM_64
        assert plan.ha_enabled is True
        assert plan.dr_enabled is True


class TestValidatePlan:
    def test_validate_plan_passes(self) -> None:
        plan = _make_plan()
        result = ValidationResult(
            status=ValidationStatus.PASSED,
            checks_passed=8,
            checks_failed=0,
            warnings=(),
            errors=(),
        )

        validated = plan.validate_plan(result)

        assert validated.validation_status == ValidationStatus.PASSED
        assert len(validated.domain_events) == 1
        event = validated.domain_events[0]
        assert isinstance(event, PlanValidatedEvent)
        assert event.checks_passed == 8
        assert event.checks_failed == 0

    def test_validate_plan_with_warnings(self) -> None:
        plan = _make_plan()
        result = ValidationResult(
            status=ValidationStatus.WARNINGS,
            checks_passed=6,
            checks_failed=0,
            warnings=("CMEK not enabled",),
            errors=(),
        )

        validated = plan.validate_plan(result)

        assert validated.validation_status == ValidationStatus.WARNINGS

    def test_validate_plan_fails(self) -> None:
        plan = _make_plan()
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            checks_passed=5,
            checks_failed=2,
            warnings=(),
            errors=("Subnet overlap", "Memory below minimum"),
        )

        validated = plan.validate_plan(result)

        assert validated.validation_status == ValidationStatus.FAILED
        event = validated.domain_events[0]
        assert isinstance(event, PlanValidatedEvent)
        assert event.checks_failed == 2


class TestMarkTerraformGenerated:
    def test_mark_terraform_generated(self) -> None:
        plan = _make_plan()
        ref = "gs://hanaforge-terraform/prog-001/plan-001/abc123.tf"

        updated = plan.mark_terraform_generated(ref)

        assert updated.terraform_plan_ref == ref
        assert plan.terraform_plan_ref is None  # original unchanged
        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, TerraformPlanGeneratedEvent)
        assert event.plan_ref == ref


class TestApprovePlan:
    def test_approve_plan_when_passed(self) -> None:
        plan = _make_plan(validation_status=ValidationStatus.PASSED)

        approved = plan.approve_plan()

        assert approved.validation_status == ValidationStatus.PASSED

    def test_approve_plan_when_warnings(self) -> None:
        plan = _make_plan(validation_status=ValidationStatus.WARNINGS)

        approved = plan.approve_plan()

        assert approved.validation_status == ValidationStatus.PASSED

    def test_cannot_approve_failed_plan(self) -> None:
        plan = _make_plan(validation_status=ValidationStatus.FAILED)

        with pytest.raises(ValueError, match="Cannot approve plan"):
            plan.approve_plan()

    def test_cannot_approve_not_validated_plan(self) -> None:
        plan = _make_plan(validation_status=ValidationStatus.NOT_VALIDATED)

        with pytest.raises(ValueError, match="Cannot approve plan"):
            plan.approve_plan()


class TestImmutability:
    def test_plan_is_immutable(self) -> None:
        original = _make_plan()
        ref = "gs://bucket/plan.tf"

        updated = original.mark_terraform_generated(ref)

        assert original.terraform_plan_ref is None
        assert updated.terraform_plan_ref == ref
        assert original.domain_events == ()
        assert len(updated.domain_events) == 1

    def test_validate_preserves_original(self) -> None:
        original = _make_plan()
        result = ValidationResult(
            status=ValidationStatus.PASSED,
            checks_passed=8,
            checks_failed=0,
            warnings=(),
            errors=(),
        )

        validated = original.validate_plan(result)

        assert original.validation_status == ValidationStatus.NOT_VALIDATED
        assert validated.validation_status == ValidationStatus.PASSED


class TestCostEstimateProperties:
    def test_total_monthly_sums_all_components(self) -> None:
        cost = CostEstimate(
            hana_monthly=10_000.00,
            app_server_monthly=2_000.00,
            storage_monthly=500.00,
            network_monthly=200.00,
            backup_monthly=50.00,
            monitoring_monthly=100.00,
            cud_discount_percentage=20.0,
        )

        expected_total = 10_000 + 2_000 + 500 + 200 + 50 + 100
        assert cost.total_monthly == expected_total

    def test_total_annual(self) -> None:
        cost = CostEstimate(
            hana_monthly=10_000.00,
            app_server_monthly=2_000.00,
            storage_monthly=500.00,
            network_monthly=200.00,
            backup_monthly=50.00,
            monitoring_monthly=100.00,
            cud_discount_percentage=20.0,
        )

        assert cost.total_annual == cost.total_monthly * 12

    def test_cud_monthly_applies_discount(self) -> None:
        cost = CostEstimate(
            hana_monthly=10_000.00,
            app_server_monthly=2_000.00,
            storage_monthly=500.00,
            network_monthly=200.00,
            backup_monthly=50.00,
            monitoring_monthly=100.00,
            cud_discount_percentage=37.0,
        )

        expected_cud = cost.total_monthly * 0.63
        assert abs(cost.cud_monthly - expected_cud) < 0.01
