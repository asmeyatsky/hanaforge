"""MCP server for Discovery Intelligence (Module 01).

Exposes SAP landscape discovery capabilities as MCP tools and resources,
allowing AI agents to initiate discovery runs, check status, and read
landscape/object inventory data.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from infrastructure.config.dependency_injection import Container


def create_discovery_server(container: Container) -> Server:
    """Build and return an MCP Server wired to the discovery use cases."""

    server = Server("hanaforge-discovery")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="run_discovery",
                description=(
                    "Initiate SAP landscape discovery for a programme. "
                    "Connects to the SAP system, extracts custom objects, "
                    "integration points, and system metadata."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                        "connection_params": {
                            "type": "object",
                            "description": "SAP connection parameters (host, system_number, client, user, password)",
                            "properties": {
                                "host": {"type": "string"},
                                "system_number": {"type": "string"},
                                "client": {"type": "string"},
                                "user": {"type": "string"},
                                "password": {"type": "string"},
                            },
                            "required": ["host", "system_number", "client", "user", "password"],
                        },
                    },
                    "required": ["programme_id", "connection_params"],
                },
            ),
            Tool(
                name="get_discovery_status",
                description=(
                    "Check the current status of a discovery run for a programme."
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
        if name == "run_discovery":
            use_case = container.resolve("StartDiscoveryUseCase")
            result = await use_case.execute(
                programme_id=arguments["programme_id"],
                connection_params=arguments["connection_params"],
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "get_discovery_status":
            programme_repo = container.resolve("ProgrammeRepositoryPort")
            programme = await programme_repo.get_by_id(arguments["programme_id"])
            if programme is None:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": "Programme not found"}),
                    )
                ]
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "programme_id": programme.id,
                            "status": programme.status.value,
                            "name": programme.name,
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
                uri="discovery://{programme_id}/landscape",
                name="Landscape Data",
                description="Read landscape data for a programme",
                mimeType="application/json",
            ),
            Resource(
                uri="discovery://{programme_id}/objects",
                name="Object Inventory",
                description="Read custom object inventory for a programme",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        # Parse URI: discovery://<programme_id>/<resource_type>
        parts = str(uri).replace("discovery://", "").split("/")
        if len(parts) < 2:
            return json.dumps({"error": "Invalid resource URI"})

        programme_id = parts[0]
        resource_type = parts[1]

        if resource_type == "landscape":
            landscape_repo = container.resolve("LandscapeRepositoryPort")
            landscapes = await landscape_repo.list_by_programme(programme_id)
            data = []
            for ls in landscapes:
                data.append(
                    {
                        "id": ls.id,
                        "system_id": ls.system_id,
                        "system_role": ls.system_role.value,
                        "db_size_gb": ls.db_size_gb,
                        "number_of_users": ls.number_of_users,
                        "custom_object_count": ls.custom_object_count,
                        "integration_points": list(ls.integration_points),
                    }
                )
            return json.dumps(data, indent=2)

        if resource_type == "objects":
            landscape_repo = container.resolve("LandscapeRepositoryPort")
            object_repo = container.resolve("CustomObjectRepositoryPort")

            landscapes = await landscape_repo.list_by_programme(programme_id)
            all_objects: list[dict] = []
            for ls in landscapes:
                objects = await object_repo.list_by_landscape(ls.id)
                for obj in objects:
                    all_objects.append(
                        {
                            "id": obj.id,
                            "object_name": obj.object_name,
                            "object_type": obj.object_type.value,
                            "package_name": obj.package_name,
                            "domain": obj.domain.value,
                            "compatibility_status": obj.compatibility_status.value,
                            "remediation_status": obj.remediation_status.value,
                        }
                    )
            return json.dumps(all_objects, indent=2)

        return json.dumps({"error": f"Unknown resource type: {resource_type}"})

    return server
