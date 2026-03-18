"""TestGenerationService — pure domain logic for creating test scenarios and traceability."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.entities.test_scenario import TestScenario
from domain.value_objects.test_types import (
    InterfaceTestType,
    ProcessArea,
    TestPriority,
    TestStatus,
    TestStep,
    TraceabilityEntry,
)


class TestGenerationService:
    """Pure domain service: transforms business process definitions into test scenarios."""

    def create_scenario_from_process(
        self,
        process_def: dict,
        process_area: ProcessArea,
    ) -> TestScenario:
        """Create a structured test scenario from a business process definition."""
        scenario_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        steps_raw: list[dict] = process_def.get("steps", [])
        steps = tuple(
            TestStep(
                step_number=i + 1,
                action=s.get("action", ""),
                expected_result=s.get("expected_result", ""),
                sap_transaction=s.get("sap_transaction"),
                test_data=s.get("test_data"),
            )
            for i, s in enumerate(steps_raw)
        )

        return TestScenario(
            id=scenario_id,
            programme_id=process_def.get("programme_id", ""),
            process_area=process_area,
            scenario_name=process_def.get("name", "Unnamed Scenario"),
            description=process_def.get("description", ""),
            preconditions=tuple(process_def.get("preconditions", [])),
            steps=steps,
            expected_outcome=process_def.get("expected_outcome", ""),
            sap_transaction=process_def.get("sap_transaction"),
            fiori_app_id=process_def.get("fiori_app_id"),
            priority=TestPriority(process_def.get("priority", "MEDIUM")),
            status=TestStatus.DRAFT,
            tags=tuple(process_def.get("tags", [])),
            created_at=now,
        )

    def generate_interface_test(
        self,
        interface_type: InterfaceTestType,
        interface_name: str,
        interface_config: dict,
    ) -> TestScenario:
        """Create a test scenario for IDoc/RFC/BAPI/REST/OData interfaces."""
        scenario_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        steps = (
            TestStep(
                step_number=1,
                action=f"Send test message via {interface_type.value} interface '{interface_name}'",
                expected_result="Message received and processed successfully",
                sap_transaction=interface_config.get("sap_transaction"),
            ),
            TestStep(
                step_number=2,
                action=f"Verify {interface_type.value} message payload structure",
                expected_result="All mandatory fields present and correctly formatted",
            ),
            TestStep(
                step_number=3,
                action=f"Validate {interface_type.value} response / status update",
                expected_result=interface_config.get("expected_response", "Success status returned"),
            ),
        )

        return TestScenario(
            id=scenario_id,
            programme_id=interface_config.get("programme_id", ""),
            process_area=ProcessArea.INTEGRATION,
            scenario_name=f"{interface_type.value} Test: {interface_name}",
            description=interface_config.get(
                "description",
                f"Integration test for {interface_type.value} interface '{interface_name}'",
            ),
            preconditions=tuple(
                interface_config.get(
                    "preconditions",
                    [
                        f"{interface_type.value} interface '{interface_name}' is active",
                        "Test data is prepared in source system",
                    ],
                )
            ),
            steps=steps,
            expected_outcome=interface_config.get(
                "expected_outcome",
                f"{interface_type.value} message processed end-to-end without errors",
            ),
            sap_transaction=interface_config.get("sap_transaction"),
            fiori_app_id=None,
            priority=TestPriority(interface_config.get("priority", "HIGH")),
            status=TestStatus.DRAFT,
            tags=(interface_type.value, "INTEGRATION", interface_name),
            created_at=now,
        )

    def build_traceability_matrix(
        self,
        processes: list[dict],
        scenarios: list[TestScenario],
    ) -> list[TraceabilityEntry]:
        """Map business processes to test scenarios, producing a traceability matrix."""
        # Index scenarios by process name for O(1) lookup
        scenario_by_name: dict[str, list[TestScenario]] = {}
        for scenario in scenarios:
            key = scenario.scenario_name.lower()
            scenario_by_name.setdefault(key, []).append(scenario)

        entries: list[TraceabilityEntry] = []
        for process in processes:
            process_id = process.get("id", "")
            process_name = process.get("name", "")

            # Find matching scenarios by process name or tags
            matched = scenario_by_name.get(process_name.lower(), [])
            if not matched:
                # Try partial matching via tags or description
                for scenario in scenarios:
                    if process_name.lower() in scenario.description.lower():
                        matched.append(scenario)
                    elif any(process_name.lower() in t.lower() for t in scenario.tags):
                        matched.append(scenario)

            if matched:
                for scenario in matched:
                    defect_ids = tuple(tag.replace("defect:", "") for tag in scenario.tags if tag.startswith("defect:"))
                    entries.append(
                        TraceabilityEntry(
                            process_id=process_id,
                            process_name=process_name,
                            test_scenario_id=scenario.id,
                            test_scenario_name=scenario.scenario_name,
                            defect_ids=defect_ids,
                            coverage_status="COVERED",
                        )
                    )
            else:
                entries.append(
                    TraceabilityEntry(
                        process_id=process_id,
                        process_name=process_name,
                        test_scenario_id="",
                        test_scenario_name="",
                        defect_ids=(),
                        coverage_status="NOT_COVERED",
                    )
                )

        return entries
