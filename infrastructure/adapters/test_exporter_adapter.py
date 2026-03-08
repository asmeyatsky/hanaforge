"""TestExporterAdapter — implements TestExporterPort with multi-format export support.

Supports: Jira Xray (JSON), Azure DevOps (CSV), HP ALM (XML), Tricentis Tosca (XML), CSV.
"""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET

from domain.entities.test_scenario import TestScenario
from domain.value_objects.test_types import TestExportFormat


class TestExporterAdapter:
    """Dispatches export to the appropriate format handler."""

    async def export_scenarios(
        self,
        scenarios: list[TestScenario],
        format: TestExportFormat,
    ) -> bytes:
        dispatch = {
            TestExportFormat.JIRA_XRAY: self._export_to_jira_xray,
            TestExportFormat.AZURE_DEVOPS: self._export_to_azure_devops,
            TestExportFormat.HP_ALM: self._export_to_hp_alm,
            TestExportFormat.TRICENTIS_TOSCA: self._export_to_tricentis_tosca,
            TestExportFormat.CSV: self._export_to_csv,
        }
        handler = dispatch.get(format)
        if handler is None:
            raise ValueError(f"Unsupported export format: {format.value}")
        return handler(scenarios)

    # ------------------------------------------------------------------
    # Jira Xray — JSON format
    # ------------------------------------------------------------------

    @staticmethod
    def _export_to_jira_xray(scenarios: list[TestScenario]) -> bytes:
        tests = []
        for s in scenarios:
            steps = [
                {
                    "action": step.action,
                    "data": step.test_data or "",
                    "result": step.expected_result,
                }
                for step in s.steps
            ]
            tests.append(
                {
                    "testtype": "Manual",
                    "fields": {
                        "summary": s.scenario_name,
                        "description": s.description,
                        "priority": {"name": s.priority.value.capitalize()},
                        "labels": list(s.tags),
                    },
                    "xpieces": {
                        "steps": steps,
                    },
                    "precondition": "; ".join(s.preconditions),
                }
            )
        payload = {"tests": tests}
        return json.dumps(payload, indent=2).encode("utf-8")

    # ------------------------------------------------------------------
    # Azure DevOps — CSV format
    # ------------------------------------------------------------------

    @staticmethod
    def _export_to_azure_devops(scenarios: list[TestScenario]) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Work Item Type", "Title", "Description", "Priority",
            "State", "Steps", "Area Path", "Tags",
        ])
        for s in scenarios:
            steps_xml = "".join(
                f"<step id='{step.step_number}' type='ActionStep'>"
                f"<parameterizedString>{step.action}</parameterizedString>"
                f"<parameterizedString>{step.expected_result}</parameterizedString>"
                f"</step>"
                for step in s.steps
            )
            writer.writerow([
                s.id,
                "Test Case",
                s.scenario_name,
                s.description,
                s.priority.value,
                s.status.value,
                f"<steps>{steps_xml}</steps>",
                s.process_area.value,
                ";".join(s.tags),
            ])
        return output.getvalue().encode("utf-8")

    # ------------------------------------------------------------------
    # HP ALM — XML format
    # ------------------------------------------------------------------

    @staticmethod
    def _export_to_hp_alm(scenarios: list[TestScenario]) -> bytes:
        root = ET.Element("Tests")
        for s in scenarios:
            test_el = ET.SubElement(root, "Test")
            ET.SubElement(test_el, "Name").text = s.scenario_name
            ET.SubElement(test_el, "Description").text = s.description
            ET.SubElement(test_el, "Priority").text = s.priority.value
            ET.SubElement(test_el, "Status").text = s.status.value
            ET.SubElement(test_el, "Type").text = "MANUAL"
            ET.SubElement(test_el, "SAPTransaction").text = s.sap_transaction or ""
            ET.SubElement(test_el, "FioriAppID").text = s.fiori_app_id or ""

            steps_el = ET.SubElement(test_el, "DesignSteps")
            for step in s.steps:
                step_el = ET.SubElement(steps_el, "DesignStep")
                ET.SubElement(step_el, "StepOrder").text = str(step.step_number)
                ET.SubElement(step_el, "StepDescription").text = step.action
                ET.SubElement(step_el, "ExpectedResult").text = step.expected_result

        tree = ET.ElementTree(root)
        buffer = io.BytesIO()
        tree.write(buffer, encoding="utf-8", xml_declaration=True)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # Tricentis Tosca — XML format
    # ------------------------------------------------------------------

    @staticmethod
    def _export_to_tricentis_tosca(scenarios: list[TestScenario]) -> bytes:
        root = ET.Element("ToscaTestCases")
        for s in scenarios:
            tc = ET.SubElement(root, "TestCase", Name=s.scenario_name)
            ET.SubElement(tc, "Description").text = s.description
            ET.SubElement(tc, "Priority").text = s.priority.value
            ET.SubElement(tc, "Preconditions").text = "; ".join(s.preconditions)

            steps_el = ET.SubElement(tc, "TestSteps")
            for step in s.steps:
                step_el = ET.SubElement(steps_el, "TestStep", Number=str(step.step_number))
                ET.SubElement(step_el, "Action").text = step.action
                ET.SubElement(step_el, "ExpectedResult").text = step.expected_result
                if step.sap_transaction:
                    ET.SubElement(step_el, "SAPTransaction").text = step.sap_transaction
                if step.test_data:
                    ET.SubElement(step_el, "TestData").text = step.test_data

        tree = ET.ElementTree(root)
        buffer = io.BytesIO()
        tree.write(buffer, encoding="utf-8", xml_declaration=True)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # Generic CSV
    # ------------------------------------------------------------------

    @staticmethod
    def _export_to_csv(scenarios: list[TestScenario]) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Scenario ID", "Scenario Name", "Process Area", "Description",
            "Priority", "Status", "SAP Transaction", "Fiori App ID",
            "Step #", "Step Action", "Expected Result", "Tags",
        ])
        for s in scenarios:
            for step in s.steps:
                writer.writerow([
                    s.id,
                    s.scenario_name,
                    s.process_area.value,
                    s.description,
                    s.priority.value,
                    s.status.value,
                    s.sap_transaction or "",
                    s.fiori_app_id or "",
                    step.step_number,
                    step.action,
                    step.expected_result,
                    ";".join(s.tags),
                ])
        return output.getvalue().encode("utf-8")
