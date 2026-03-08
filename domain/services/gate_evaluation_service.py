"""GateEvaluationService — evaluates go/no-go decision gates with system health checks.

Supports thorough evaluation for each gate type:
  SYSTEM_HEALTH:          HANA availability, app server status, OS checks
  DATA_RECONCILIATION:    Record counts, checksum validation, financial balances
  INTERFACE_CONNECTIVITY: RFC destinations, IDoc processing, API health
  PERFORMANCE_BASELINE:   Response times, batch throughput, memory utilisation
  BUSINESS_SIGN_OFF:      Manual approvals (pass-through with provided results)
  FINAL_GO_LIVE:          Composite gate aggregating all check categories
"""

from __future__ import annotations

from dataclasses import replace

from domain.value_objects.cutover_types import (
    GateStatus,
    GateType,
    GoNoGoGate,
    HealthCheck,
)


class GateEvaluationService:
    """Pure domain service — no infrastructure dependencies.

    Takes a GoNoGoGate and a dict of system check results, evaluates each
    health check, and returns an updated gate with pass/fail determinations.
    """

    def evaluate_gate(
        self, gate: GoNoGoGate, system_checks: dict
    ) -> GoNoGoGate:
        """Evaluate all health checks for a gate and determine overall status.

        Args:
            gate: The go/no-go gate to evaluate.
            system_checks: Dict mapping check names (or check_types) to their
                actual values/results.  Structure varies by gate type:
                  - SYSTEM_HEALTH: {"hana_ping": "AVAILABLE", "app_server": "RUNNING", ...}
                  - DATA_RECONCILIATION: {"data_recon": {"counts": "MATCH", "checksums": "MATCH"}}
                  - INTERFACE_CONNECTIVITY: {"rfc_test": "ALL_CONNECTED", ...}
                  - PERFORMANCE_BASELINE: {"response_time": "850ms", ...}
                  - BUSINESS_SIGN_OFF: {"manual": {"team_readiness": "CONFIRMED", ...}}
                  - FINAL_GO_LIVE: Superset of all the above.

        Returns:
            Updated GoNoGoGate with evaluated checks and overall status.
        """
        evaluated_checks: list[HealthCheck] = []

        for check in gate.checks:
            evaluated = self._evaluate_single_check(check, system_checks, gate.gate_type)
            evaluated_checks.append(evaluated)

        # Determine overall gate status
        all_passed = all(c.passed is True for c in evaluated_checks)
        any_evaluated = any(c.passed is not None for c in evaluated_checks)

        if not any_evaluated:
            overall = GateStatus.NOT_EVALUATED
        elif all_passed:
            overall = GateStatus.PASSED
        else:
            overall = GateStatus.FAILED

        return replace(
            gate,
            checks=tuple(evaluated_checks),
            status=overall,
        )

    # ------------------------------------------------------------------
    # Private evaluation logic
    # ------------------------------------------------------------------

    def _evaluate_single_check(
        self,
        check: HealthCheck,
        system_checks: dict,
        gate_type: GateType,
    ) -> HealthCheck:
        """Evaluate one HealthCheck against the provided system data."""
        actual_value = self._resolve_actual_value(check, system_checks)

        if actual_value is None:
            # No data provided for this check — cannot evaluate
            return replace(check, actual_value="NOT_PROVIDED", passed=False)

        passed = self._check_passes(check, actual_value, gate_type)

        return replace(check, actual_value=str(actual_value), passed=passed)

    def _resolve_actual_value(
        self, check: HealthCheck, system_checks: dict
    ) -> str | None:
        """Look up the actual value for a check in the system_checks dict.

        Supports multiple lookup strategies:
          1. Direct match by check name
          2. Match by check_type
          3. Nested dict for check_type with sub-key matching
        """
        # Strategy 1: direct match by check name
        if check.name in system_checks:
            val = system_checks[check.name]
            if isinstance(val, dict):
                # Nested: try to find a relevant sub-key
                return self._extract_from_nested(val, check)
            return str(val)

        # Strategy 2: match by check_type
        if check.check_type in system_checks:
            val = system_checks[check.check_type]
            if isinstance(val, dict):
                return self._extract_from_nested(val, check)
            return str(val)

        return None

    def _extract_from_nested(self, nested: dict, check: HealthCheck) -> str | None:
        """Extract a value from a nested dict using check name heuristics."""
        # Try exact name match within nested
        if check.name in nested:
            return str(nested[check.name])

        # Try lowercase/normalised matching
        normalised_name = check.name.lower().replace(" ", "_")
        for key, val in nested.items():
            if key.lower().replace(" ", "_") == normalised_name:
                return str(val)

        # Fallback: if the nested dict has a single 'status' or 'value' key
        if "status" in nested:
            return str(nested["status"])
        if "value" in nested:
            return str(nested["value"])

        # Last resort: return the first value
        if nested:
            return str(next(iter(nested.values())))

        return None

    def _check_passes(
        self,
        check: HealthCheck,
        actual_value: str,
        gate_type: GateType,
    ) -> bool:
        """Determine whether an individual check passes.

        Applies gate-type-specific evaluation logic.
        """
        target = check.target_value

        # --- Threshold-based checks (numeric comparison) ---
        if target.startswith("<") or target.startswith(">") or target.startswith(">="):
            return self._evaluate_threshold(target, actual_value)

        # --- Exact match (most common) ---
        if self._normalise(actual_value) == self._normalise(target):
            return True

        # --- Gate-type-specific heuristics ---
        if gate_type == GateType.SYSTEM_HEALTH:
            return self._evaluate_system_health_check(check, actual_value)

        if gate_type == GateType.DATA_RECONCILIATION:
            return self._evaluate_data_recon_check(check, actual_value)

        if gate_type == GateType.INTERFACE_CONNECTIVITY:
            return self._evaluate_interface_check(check, actual_value)

        if gate_type == GateType.PERFORMANCE_BASELINE:
            return self._evaluate_performance_check(check, actual_value)

        if gate_type == GateType.FINAL_GO_LIVE:
            # Final gate: strict — must match target exactly
            return self._normalise(actual_value) == self._normalise(target)

        if gate_type == GateType.BUSINESS_SIGN_OFF:
            # Manual checks: accept various affirmative values
            return actual_value.upper() in (
                "CONFIRMED",
                "APPROVED",
                "YES",
                "TRUE",
                "ALL_CONFIRMED",
                "SIGNED_OFF",
                "ALL_SIGNED_OFF",
                target.upper(),
            )

        return False

    # ------------------------------------------------------------------
    # Gate-type-specific evaluation
    # ------------------------------------------------------------------

    def _evaluate_system_health_check(
        self, check: HealthCheck, actual: str
    ) -> bool:
        """SYSTEM_HEALTH gate: HANA availability, app server status, OS checks."""
        positive_indicators = {
            "AVAILABLE", "RUNNING", "HEALTHY", "OK", "UP",
            "ONLINE", "ACTIVE", "ZERO_SESSIONS", "ALL_SUSPENDED",
            "BACKUP_COMPLETE", "FREEZE_ACTIVE",
        }
        return actual.upper() in positive_indicators

    def _evaluate_data_recon_check(
        self, check: HealthCheck, actual: str
    ) -> bool:
        """DATA_RECONCILIATION gate: record counts, checksums, balances."""
        positive_indicators = {
            "COUNTS_MATCH", "CHECKSUMS_MATCH", "BALANCES_MATCH",
            "MATCH", "RECONCILED", "OK", "PASSED", "VALID",
            "ZERO_VARIANCE",
        }
        return actual.upper() in positive_indicators

    def _evaluate_interface_check(
        self, check: HealthCheck, actual: str
    ) -> bool:
        """INTERFACE_CONNECTIVITY gate: RFC, IDoc, API health."""
        positive_indicators = {
            "ALL_CONNECTED", "PROCESSING_OK", "ALL_HEALTHY",
            "CONNECTED", "HEALTHY", "OK", "ACTIVE", "UP",
        }
        return actual.upper() in positive_indicators

    def _evaluate_performance_check(
        self, check: HealthCheck, actual: str
    ) -> bool:
        """PERFORMANCE_BASELINE gate: response times, throughput, memory."""
        # Try threshold evaluation first
        target = check.target_value
        if target.startswith("<") or target.startswith(">") or target.startswith(">="):
            return self._evaluate_threshold(target, actual)

        positive_indicators = {
            "WITHIN_THRESHOLD", "OK", "HEALTHY", "PASSED",
            "ACCEPTABLE", "NORMAL",
        }
        return actual.upper() in positive_indicators

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(value: str) -> str:
        """Normalise a string for comparison."""
        return value.strip().upper().replace(" ", "_")

    @staticmethod
    def _evaluate_threshold(target: str, actual: str) -> bool:
        """Evaluate threshold expressions like '<1000ms', '>=80%', '<80%'.

        Returns True if actual satisfies the threshold condition.
        """
        # Extract numeric parts
        def extract_number(s: str) -> float | None:
            cleaned = ""
            for ch in s:
                if ch.isdigit() or ch == ".":
                    cleaned += ch
            if cleaned:
                try:
                    return float(cleaned)
                except ValueError:
                    return None
            return None

        actual_num = extract_number(actual)
        if actual_num is None:
            return False

        if target.startswith(">="):
            threshold = extract_number(target[2:])
            if threshold is not None:
                return actual_num >= threshold
        elif target.startswith(">"):
            threshold = extract_number(target[1:])
            if threshold is not None:
                return actual_num > threshold
        elif target.startswith("<="):
            threshold = extract_number(target[2:])
            if threshold is not None:
                return actual_num <= threshold
        elif target.startswith("<"):
            threshold = extract_number(target[1:])
            if threshold is not None:
                return actual_num < threshold

        return False
