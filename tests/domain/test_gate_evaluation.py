"""Tests for GateEvaluationService — pure domain logic, no mocks."""

from domain.services.gate_evaluation_service import GateEvaluationService
from domain.value_objects.cutover_types import (
    GateStatus,
    GateType,
    GoNoGoGate,
    HealthCheck,
)


def _make_service() -> GateEvaluationService:
    return GateEvaluationService()


class TestEvaluateSystemHealthGate:
    def test_evaluate_system_health_gate_passes(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-001",
            name="System Health Gate",
            gate_type=GateType.SYSTEM_HEALTH,
            checks=(
                HealthCheck(
                    name="HANA availability",
                    check_type="hana_ping",
                    target_value="AVAILABLE",
                ),
                HealthCheck(
                    name="App server status",
                    check_type="app_server",
                    target_value="RUNNING",
                ),
                HealthCheck(
                    name="All users locked",
                    check_type="user_sessions",
                    target_value="ZERO_SESSIONS",
                ),
            ),
        )

        system_checks = {
            "hana_ping": "AVAILABLE",
            "app_server": "RUNNING",
            "user_sessions": "ZERO_SESSIONS",
        }

        result = service.evaluate_gate(gate, system_checks)

        assert result.status == GateStatus.PASSED
        for check in result.checks:
            assert check.passed is True
            assert check.actual_value is not None

    def test_evaluate_gate_fails_on_check_failure(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-001",
            name="System Health Gate",
            gate_type=GateType.SYSTEM_HEALTH,
            checks=(
                HealthCheck(
                    name="HANA availability",
                    check_type="hana_ping",
                    target_value="AVAILABLE",
                ),
                HealthCheck(
                    name="App server status",
                    check_type="app_server",
                    target_value="RUNNING",
                ),
            ),
        )

        system_checks = {
            "hana_ping": "AVAILABLE",
            "app_server": "DOWN",  # This should fail
        }

        result = service.evaluate_gate(gate, system_checks)

        assert result.status == GateStatus.FAILED
        hana_check = next(c for c in result.checks if c.check_type == "hana_ping")
        app_check = next(c for c in result.checks if c.check_type == "app_server")
        assert hana_check.passed is True
        assert app_check.passed is False

    def test_missing_check_data_fails(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-001",
            name="System Health Gate",
            gate_type=GateType.SYSTEM_HEALTH,
            checks=(
                HealthCheck(
                    name="HANA availability",
                    check_type="hana_ping",
                    target_value="AVAILABLE",
                ),
            ),
        )

        # No data provided
        result = service.evaluate_gate(gate, {})

        assert result.status == GateStatus.FAILED
        assert result.checks[0].passed is False
        assert result.checks[0].actual_value == "NOT_PROVIDED"


class TestEvaluateDataReconciliationGate:
    def test_data_recon_gate_passes(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-002",
            name="Data Reconciliation Gate",
            gate_type=GateType.DATA_RECONCILIATION,
            checks=(
                HealthCheck(
                    name="Record count reconciliation",
                    check_type="data_recon",
                    target_value="COUNTS_MATCH",
                ),
                HealthCheck(
                    name="Checksum validation",
                    check_type="checksum",
                    target_value="CHECKSUMS_MATCH",
                ),
            ),
        )

        system_checks = {
            "data_recon": "COUNTS_MATCH",
            "checksum": "CHECKSUMS_MATCH",
        }

        result = service.evaluate_gate(gate, system_checks)
        assert result.status == GateStatus.PASSED

    def test_data_recon_gate_fails_on_mismatch(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-002",
            name="Data Reconciliation Gate",
            gate_type=GateType.DATA_RECONCILIATION,
            checks=(
                HealthCheck(
                    name="Record counts",
                    check_type="data_recon",
                    target_value="COUNTS_MATCH",
                ),
            ),
        )

        system_checks = {"data_recon": "COUNTS_MISMATCH"}
        result = service.evaluate_gate(gate, system_checks)
        assert result.status == GateStatus.FAILED


class TestEvaluateInterfaceConnectivityGate:
    def test_interface_gate_passes(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-003",
            name="Interface Connectivity Gate",
            gate_type=GateType.INTERFACE_CONNECTIVITY,
            checks=(
                HealthCheck(
                    name="RFC destinations",
                    check_type="rfc_test",
                    target_value="ALL_CONNECTED",
                ),
                HealthCheck(
                    name="IDoc processing",
                    check_type="idoc_test",
                    target_value="PROCESSING_OK",
                ),
                HealthCheck(
                    name="API endpoints",
                    check_type="api_health",
                    target_value="ALL_HEALTHY",
                ),
            ),
        )

        system_checks = {
            "rfc_test": "ALL_CONNECTED",
            "idoc_test": "PROCESSING_OK",
            "api_health": "ALL_HEALTHY",
        }

        result = service.evaluate_gate(gate, system_checks)
        assert result.status == GateStatus.PASSED


class TestEvaluatePerformanceBaselineGate:
    def test_performance_gate_with_thresholds(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-004",
            name="Performance Baseline Gate",
            gate_type=GateType.PERFORMANCE_BASELINE,
            checks=(
                HealthCheck(
                    name="Dialog response time",
                    check_type="response_time",
                    target_value="<1000ms",
                ),
                HealthCheck(
                    name="HANA memory",
                    check_type="hana_memory",
                    target_value="<80%",
                ),
                HealthCheck(
                    name="Batch throughput",
                    check_type="batch_throughput",
                    target_value=">=80%",
                ),
            ),
        )

        system_checks = {
            "response_time": "850ms",
            "hana_memory": "62%",
            "batch_throughput": "92%",
        }

        result = service.evaluate_gate(gate, system_checks)
        assert result.status == GateStatus.PASSED

    def test_performance_gate_fails_threshold(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-004",
            name="Performance Gate",
            gate_type=GateType.PERFORMANCE_BASELINE,
            checks=(
                HealthCheck(
                    name="Response time",
                    check_type="response_time",
                    target_value="<1000ms",
                ),
            ),
        )

        system_checks = {"response_time": "1500ms"}
        result = service.evaluate_gate(gate, system_checks)
        assert result.status == GateStatus.FAILED


class TestEvaluateBusinessSignOffGate:
    def test_business_sign_off_passes(self) -> None:
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-005",
            name="Business Sign-Off Gate",
            gate_type=GateType.BUSINESS_SIGN_OFF,
            checks=(
                HealthCheck(
                    name="Team readiness",
                    check_type="manual",
                    target_value="ALL_CONFIRMED",
                ),
            ),
        )

        system_checks = {"manual": "ALL_CONFIRMED"}
        result = service.evaluate_gate(gate, system_checks)
        assert result.status == GateStatus.PASSED


class TestAllGateTypesSupported:
    def test_all_gate_types_supported(self) -> None:
        """Ensure every GateType enum value can be evaluated without error."""
        service = _make_service()

        for gate_type in GateType:
            gate = GoNoGoGate(
                id=f"GATE-{gate_type.value}",
                name=f"Test {gate_type.value} Gate",
                gate_type=gate_type,
                checks=(
                    HealthCheck(
                        name="Test check",
                        check_type="test",
                        target_value="OK",
                    ),
                ),
            )

            system_checks = {"test": "OK"}
            result = service.evaluate_gate(gate, system_checks)

            # Should evaluate without exceptions
            assert result.status in (GateStatus.PASSED, GateStatus.FAILED)
            assert len(result.checks) == 1
            assert result.checks[0].actual_value is not None


class TestNestedCheckResolution:
    def test_nested_dict_resolution(self) -> None:
        """System checks can provide nested dicts."""
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-NESTED",
            name="Nested Gate",
            gate_type=GateType.SYSTEM_HEALTH,
            checks=(
                HealthCheck(
                    name="HANA status",
                    check_type="hana",
                    target_value="AVAILABLE",
                ),
            ),
        )

        system_checks = {"hana": {"status": "AVAILABLE"}}
        result = service.evaluate_gate(gate, system_checks)
        assert result.status == GateStatus.PASSED

    def test_check_by_name_lookup(self) -> None:
        """System checks can be looked up by check name."""
        service = _make_service()
        gate = GoNoGoGate(
            id="GATE-NAME",
            name="Name Lookup Gate",
            gate_type=GateType.SYSTEM_HEALTH,
            checks=(
                HealthCheck(
                    name="HANA availability",
                    check_type="hana_ping",
                    target_value="AVAILABLE",
                ),
            ),
        )

        # Provide by name instead of check_type
        system_checks = {"HANA availability": "AVAILABLE"}
        result = service.evaluate_gate(gate, system_checks)
        assert result.status == GateStatus.PASSED
