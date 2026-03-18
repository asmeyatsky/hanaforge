"""MCP server for TestForge SAP Edition (Module 04).

Exposes test generation, interface testing, and export capabilities as MCP tools
and resources, allowing AI agents to generate, query, and export test scenarios.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from infrastructure.config.dependency_injection import Container


def create_testforge_server(container: Container) -> Server:
    """Build and return an MCP Server wired to the TestForge use cases."""

    server = Server("hanaforge-testforge")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="generate_tests",
                description=(
                    "Generate end-to-end test scenarios for SAP business processes. "
                    "Supports OTC, P2P, RTR, H2R, and Plan-to-Produce process areas."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                        "process_area": {
                            "type": "string",
                            "description": (
                                "Process area to generate tests for "
                                "(ORDER_TO_CASH, PROCURE_TO_PAY, RECORD_TO_REPORT, "
                                "HIRE_TO_RETIRE, PLAN_TO_PRODUCE). "
                                "Omit to generate for all areas."
                            ),
                        },
                        "process_definitions": {
                            "type": "array",
                            "description": "List of business process definitions",
                            "items": {"type": "object"},
                        },
                        "sap_version": {
                            "type": "string",
                            "description": "Target SAP S/4HANA version (e.g. S/4HANA 2023)",
                            "default": "S/4HANA 2023",
                        },
                    },
                    "required": ["programme_id", "process_definitions"],
                },
            ),
            Tool(
                name="generate_interface_tests",
                description=("Generate test cases for SAP interface types: IDoc, RFC, BAPI, REST API, OData."),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                        "interfaces": {
                            "type": "array",
                            "description": ("List of interface definitions with type, name, and config"),
                            "items": {"type": "object"},
                        },
                    },
                    "required": ["programme_id", "interfaces"],
                },
            ),
            Tool(
                name="export_tests",
                description=(
                    "Export test scenarios to a test management tool format: "
                    "JIRA_XRAY, AZURE_DEVOPS, HP_ALM, TRICENTIS_TOSCA, or CSV."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                        "format": {
                            "type": "string",
                            "description": "Export format (JIRA_XRAY, AZURE_DEVOPS, HP_ALM, TRICENTIS_TOSCA, CSV)",
                        },
                        "process_area": {
                            "type": "string",
                            "description": "Optional process area filter",
                        },
                    },
                    "required": ["programme_id", "format"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "generate_tests":
            from domain.value_objects.test_types import ProcessArea

            use_case = container.resolve("GenerateTestScenariosUseCase")
            area_str = arguments.get("process_area")
            area = ProcessArea(area_str) if area_str else None
            result = await use_case.execute(
                programme_id=arguments["programme_id"],
                process_area=area,
                process_definitions=arguments["process_definitions"],
                sap_version=arguments.get("sap_version", "S/4HANA 2023"),
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "generate_interface_tests":
            use_case = container.resolve("GenerateInterfaceTestsUseCase")
            result = await use_case.execute(
                programme_id=arguments["programme_id"],
                interfaces=arguments["interfaces"],
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "export_tests":
            from domain.value_objects.test_types import ProcessArea, TestExportFormat

            use_case = container.resolve("ExportTestScenariosUseCase")
            area_str = arguments.get("process_area")
            area = ProcessArea(area_str) if area_str else None
            export_format = TestExportFormat(arguments["format"])
            result_bytes = await use_case.execute(
                programme_id=arguments["programme_id"],
                format=export_format,
                process_area=area,
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "exported",
                            "format": arguments["format"],
                            "size_bytes": len(result_bytes),
                        },
                        indent=2,
                    ),
                )
            ]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="tests://{programme_id}/scenarios",
                name="Test Scenarios",
                description="List test scenarios for a programme",
                mimeType="application/json",
            ),
            Resource(
                uri="tests://{programme_id}/traceability",
                name="Traceability Matrix",
                description="View traceability matrix for a programme",
                mimeType="application/json",
            ),
            Resource(
                uri="tests://{programme_id}/suites",
                name="Test Suites",
                description="List test suites for a programme",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        parts = str(uri).replace("tests://", "").split("/")
        if len(parts) < 2:
            return json.dumps({"error": "Invalid resource URI"})

        programme_id = parts[0]
        resource_type = parts[1]

        if resource_type == "scenarios":
            query = container.resolve("GetTestResultsQuery")
            result = await query.execute(programme_id=programme_id)
            return result.model_dump_json(indent=2)

        if resource_type == "traceability":
            query = container.resolve("GetTraceabilityMatrixQuery")
            result = await query.execute(programme_id=programme_id)
            return result.model_dump_json(indent=2)

        if resource_type == "suites":
            suite_repo = container.resolve("TestSuiteRepositoryPort")
            suites = await suite_repo.list_by_programme(programme_id)
            data = [
                {
                    "id": s.id,
                    "name": s.name,
                    "process_area": s.process_area.value,
                    "scenario_count": len(s.scenarios),
                    "coverage_percentage": s.coverage_percentage,
                }
                for s in suites
            ]
            return json.dumps(data, indent=2)

        return json.dumps({"error": f"Unknown resource type: {resource_type}"})

    return server
