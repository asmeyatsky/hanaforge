"""MCP server for Migration Orchestrator (Module 06).

Exposes migration planning, execution, and monitoring capabilities as MCP tools
and resources, allowing AI agents to orchestrate SAP migration workflows.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from infrastructure.config.dependency_injection import Container


def create_migration_orchestrator_server(container: Container) -> Server:
    """Build and return an MCP Server wired to the migration orchestrator use cases."""

    server = Server("hanaforge-migration-orchestrator")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="create_migration_plan",
                description=(
                    "Generate a full migration task graph for a programme. "
                    "Builds the DAG of tasks based on migration approach "
                    "(BROWNFIELD, SELECTIVE_DATA_TRANSITION, GREENFIELD) with "
                    "dependencies and critical path analysis."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                        "approach": {
                            "type": "string",
                            "enum": [
                                "BROWNFIELD",
                                "SELECTIVE_DATA_TRANSITION",
                                "GREENFIELD",
                                "RISE_WITH_SAP",
                            ],
                            "description": "Migration approach to use",
                        },
                        "landscape_metadata": {
                            "type": "object",
                            "description": (
                                "Optional landscape metadata: data_domains (list), "
                                "db_size_gb (int), system_count (int)"
                            ),
                        },
                    },
                    "required": ["programme_id", "approach"],
                },
            ),
            Tool(
                name="execute_step",
                description=(
                    "Execute a single migration task. Validates dependencies "
                    "are complete, runs the task, checks for anomalies, and "
                    "records audit entries."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the migration task to execute",
                        },
                    },
                    "required": ["task_id"],
                },
            ),
            Tool(
                name="run_batch",
                description=(
                    "Execute all ready migration tasks in parallel batches. "
                    "Finds tasks with satisfied dependencies and runs them "
                    "concurrently, continuing until no more tasks are ready."
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
            Tool(
                name="acknowledge_anomaly",
                description=(
                    "Acknowledge an anomaly alert, marking it as reviewed."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "alert_id": {
                            "type": "string",
                            "description": "ID of the anomaly alert to acknowledge",
                        },
                    },
                    "required": ["alert_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "create_migration_plan":
            from application.commands.create_migration_plan import CreateMigrationPlanUseCase
            from application.dtos.migration_dto import CreateMigrationPlanRequest

            use_case: CreateMigrationPlanUseCase = container.resolve(
                "CreateMigrationPlanUseCase"
            )
            request = CreateMigrationPlanRequest(
                approach=arguments["approach"],
                landscape_metadata=arguments.get("landscape_metadata", {}),
            )
            result = await use_case.execute(
                programme_id=arguments["programme_id"],
                request=request,
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "execute_step":

            use_case = container.resolve("ExecuteMigrationStepUseCase")
            result = await use_case.execute(task_id=arguments["task_id"])
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "run_batch":

            use_case = container.resolve("RunMigrationBatchUseCase")
            result = await use_case.execute(programme_id=arguments["programme_id"])
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "acknowledge_anomaly":
            anomaly_repo = container.resolve("AnomalyRepositoryPort")
            await anomaly_repo.acknowledge(arguments["alert_id"])
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "acknowledged",
                            "alert_id": arguments["alert_id"],
                        },
                        indent=2,
                    ),
                )
            ]

        return [
            TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"}),
            )
        ]

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="migration://{programme_id}/status",
                name="Migration Status",
                description="Full migration status including health, critical path, and task summary",
                mimeType="application/json",
            ),
            Resource(
                uri="migration://{programme_id}/tasks",
                name="Migration Tasks",
                description="List of all migration tasks for a programme",
                mimeType="application/json",
            ),
            Resource(
                uri="migration://{programme_id}/audit-log",
                name="Audit Log",
                description="Migration audit log for compliance and traceability",
                mimeType="application/json",
            ),
            Resource(
                uri="migration://{programme_id}/anomalies",
                name="Active Anomalies",
                description="Active (unacknowledged) anomaly alerts for a programme",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        # Parse URI: migration://<programme_id>/<resource_type>
        parts = str(uri).replace("migration://", "").split("/")
        if len(parts) < 2:
            return json.dumps({"error": "Invalid resource URI"})

        programme_id = parts[0]
        resource_type = parts[1]

        if resource_type == "status":
            from application.queries.get_migration_status import GetMigrationStatusQuery

            query: GetMigrationStatusQuery = container.resolve(
                "GetMigrationStatusQuery"
            )
            result = await query.execute(programme_id=programme_id)
            return result.model_dump_json(indent=2)

        if resource_type == "tasks":
            task_repo = container.resolve("MigrationTaskRepositoryPort")
            tasks = await task_repo.list_by_programme(programme_id)
            from application.dtos.migration_dto import MigrationTaskResponse

            task_data = [
                MigrationTaskResponse.from_entity(t).model_dump() for t in tasks
            ]
            return json.dumps(task_data, indent=2)

        if resource_type == "audit-log":

            query = container.resolve("GetAuditLogQuery")
            result = await query.execute(programme_id=programme_id)
            return result.model_dump_json(indent=2)

        if resource_type == "anomalies":
            anomaly_repo = container.resolve("AnomalyRepositoryPort")
            anomalies = await anomaly_repo.list_active(programme_id)
            from application.dtos.migration_dto import AnomalyAlertResponse

            data = [
                AnomalyAlertResponse.from_value_object(a).model_dump()
                for a in anomalies
            ]
            return json.dumps(data, indent=2)

        return json.dumps({"error": f"Unknown resource type: {resource_type}"})

    return server
