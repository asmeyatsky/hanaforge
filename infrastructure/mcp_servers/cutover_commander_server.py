"""MCP server for Cutover Commander (Module 07).

Exposes cutover lifecycle capabilities as MCP tools and resources,
allowing AI agents to generate runbooks, execute cutovers, evaluate gates,
manage hypercare, and generate lessons-learned documentation.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from infrastructure.config.dependency_injection import Container


def create_cutover_commander_server(container: Container) -> Server:
    """Build and return an MCP Server wired to the cutover use cases."""

    server = Server("hanaforge-cutover-commander")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="generate_runbook",
                description=(
                    "Generate a structured SAP cutover runbook from programme "
                    "artefacts including migration tasks, integration inventory, "
                    "and data migration sequences."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                        "artefacts": {
                            "type": "object",
                            "description": (
                                "Programme artefacts "
                                "(migration_tasks, integration_inventory, data_sequences)"
                            ),
                            "properties": {
                                "migration_tasks": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                },
                                "integration_inventory": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                },
                                "data_sequences": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                },
                            },
                        },
                    },
                    "required": ["programme_id", "artefacts"],
                },
            ),
            Tool(
                name="approve_runbook",
                description="Approve a cutover runbook for execution.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "runbook_id": {
                            "type": "string",
                            "description": "ID of the runbook to approve",
                        },
                        "approver": {
                            "type": "string",
                            "description": "Name/ID of the approver",
                        },
                    },
                    "required": ["runbook_id", "approver"],
                },
            ),
            Tool(
                name="start_cutover",
                description="Start cutover execution from an approved runbook.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "runbook_id": {
                            "type": "string",
                            "description": "ID of the approved runbook",
                        },
                    },
                    "required": ["runbook_id"],
                },
            ),
            Tool(
                name="evaluate_gate",
                description=(
                    "Evaluate a go/no-go decision gate with system health checks. "
                    "Checks HANA availability, interface connectivity, data reconciliation, "
                    "and performance baselines."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "ID of the running cutover execution",
                        },
                        "gate_id": {
                            "type": "string",
                            "description": "ID of the gate to evaluate",
                        },
                        "checks": {
                            "type": "object",
                            "description": "System check results keyed by check type",
                        },
                    },
                    "required": ["execution_id", "gate_id", "checks"],
                },
            ),
            Tool(
                name="update_task",
                description="Update the status of a cutover task during execution.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "ID of the cutover execution",
                        },
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to update",
                        },
                        "status": {
                            "type": "string",
                            "enum": [
                                "NOT_STARTED",
                                "IN_PROGRESS",
                                "COMPLETED",
                                "SKIPPED",
                                "FAILED",
                            ],
                            "description": "New task status",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes about the status change",
                        },
                    },
                    "required": ["execution_id", "task_id", "status"],
                },
            ),
            Tool(
                name="start_hypercare",
                description=(
                    "Start a hypercare monitoring session for a programme. "
                    "Default duration is 90 days."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                        "duration_days": {
                            "type": "integer",
                            "description": "Duration of hypercare in days (default 90)",
                            "default": 90,
                        },
                        "config": {
                            "type": "object",
                            "description": "Monitoring configuration",
                        },
                    },
                    "required": ["programme_id"],
                },
            ),
            Tool(
                name="log_incident",
                description="Log an incident during the hypercare period.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID of the hypercare session",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                            "description": "Incident severity",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the incident",
                        },
                    },
                    "required": ["session_id", "severity", "description"],
                },
            ),
            Tool(
                name="generate_lessons_learned",
                description=(
                    "Analyse cutover execution and hypercare incidents to "
                    "generate lessons-learned documentation."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                    },
                    "required": ["programme_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "generate_runbook":
                use_case = container.resolve("GenerateRunbookUseCase")
                artefacts = arguments.get("artefacts", {})
                result = await use_case.execute(
                    programme_id=arguments["programme_id"],
                    migration_tasks=artefacts.get("migration_tasks", []),
                    integration_inventory=artefacts.get("integration_inventory", []),
                    data_sequences=artefacts.get("data_sequences", []),
                )
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "approve_runbook":
                use_case = container.resolve("ApproveRunbookUseCase")
                result = await use_case.execute(
                    runbook_id=arguments["runbook_id"],
                    approver=arguments["approver"],
                )
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "start_cutover":
                use_case = container.resolve("StartCutoverUseCase")
                result = await use_case.execute(runbook_id=arguments["runbook_id"])
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "evaluate_gate":
                use_case = container.resolve("EvaluateGateUseCase")
                result = await use_case.execute(
                    execution_id=arguments["execution_id"],
                    gate_id=arguments["gate_id"],
                    system_checks=arguments.get("checks", {}),
                )
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "update_task":
                use_case = container.resolve("UpdateCutoverTaskUseCase")
                result = await use_case.execute(
                    execution_id=arguments["execution_id"],
                    task_id=arguments["task_id"],
                    status=arguments["status"],
                    notes=arguments.get("notes"),
                )
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "start_hypercare":
                use_case = container.resolve("StartHypercareUseCase")
                result = await use_case.execute(
                    programme_id=arguments["programme_id"],
                    duration_days=arguments.get("duration_days", 90),
                    monitoring_config=arguments.get("config"),
                )
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "log_incident":
                use_case = container.resolve("LogHypercareIncidentUseCase")
                result = await use_case.execute(
                    session_id=arguments["session_id"],
                    severity=arguments["severity"],
                    description=arguments["description"],
                    sap_component=arguments.get("sap_component"),
                )
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            if name == "generate_lessons_learned":
                use_case = container.resolve("GenerateLessonsLearnedUseCase")
                result = await use_case.execute(
                    programme_id=arguments["programme_id"],
                )
                return [TextContent(type="text", text=result.model_dump_json(indent=2))]

            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"}),
                )
            ]
        except Exception as exc:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(exc)}),
                )
            ]

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="cutover://{programme_id}/status",
                name="Cutover Status",
                description="Real-time cutover execution status for a programme",
                mimeType="application/json",
            ),
            Resource(
                uri="cutover://{programme_id}/runbook",
                name="Cutover Runbook",
                description="Current cutover runbook for a programme",
                mimeType="application/json",
            ),
            Resource(
                uri="cutover://{programme_id}/hypercare",
                name="Hypercare Status",
                description="Active hypercare session status for a programme",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        parts = str(uri).replace("cutover://", "").split("/")
        if len(parts) < 2:
            return json.dumps({"error": "Invalid resource URI"})

        programme_id = parts[0]
        resource_type = parts[1]

        try:
            if resource_type == "status":
                query = container.resolve("GetCutoverStatusQuery")
                result = await query.execute(programme_id)
                return result.model_dump_json(indent=2)

            if resource_type == "runbook":
                runbook_repo = container.resolve("RunbookRepositoryPort")
                runbook = await runbook_repo.get_latest_by_programme(programme_id)
                if runbook is None:
                    return json.dumps({"error": "No runbook found"})
                from application.dtos.cutover_dto import RunbookResponse

                return RunbookResponse.from_entity(runbook).model_dump_json(indent=2)

            if resource_type == "hypercare":
                query = container.resolve("GetHypercareStatusQuery")
                result = await query.execute(programme_id)
                if result is None:
                    return json.dumps({"error": "No active hypercare session"})
                return result.model_dump_json(indent=2)

            return json.dumps({"error": f"Unknown resource type: {resource_type}"})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return server
