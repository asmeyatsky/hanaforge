"""MCP server for ABAP Code Intelligence (Module 02).

Exposes ABAP analysis and source upload capabilities as MCP tools and
resources, enabling AI agents to trigger code analysis, upload source
archives, and read analysis results.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from infrastructure.config.dependency_injection import Container


def create_abap_intelligence_server(container: Container) -> Server:
    """Build and return an MCP Server wired to the ABAP analysis use cases."""

    server = Server("hanaforge-abap-intelligence")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="analyze_abap",
                description=(
                    "Run AI-powered ABAP code analysis on all custom objects "
                    "in a landscape. Identifies incompatible APIs, generates "
                    "remediation suggestions, and scores complexity."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "landscape_id": {
                            "type": "string",
                            "description": "ID of the SAP landscape containing the objects",
                        },
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the parent migration programme",
                        },
                    },
                    "required": ["landscape_id", "programme_id"],
                },
            ),
            Tool(
                name="upload_source",
                description=(
                    "Upload an ABAP source ZIP archive for a landscape. "
                    "The ZIP is parsed, objects are extracted and persisted."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "landscape_id": {
                            "type": "string",
                            "description": "ID of the target SAP landscape",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Local path to the ABAP source ZIP file",
                        },
                    },
                    "required": ["landscape_id", "file_path"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "analyze_abap":
            use_case = container.resolve("RunABAPAnalysisUseCase")
            result = await use_case.execute(
                landscape_id=arguments["landscape_id"],
                programme_id=arguments["programme_id"],
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "upload_source":
            use_case = container.resolve("UploadABAPSourceUseCase")

            # Read file from local path
            file_path = arguments["file_path"]
            try:
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
            except FileNotFoundError:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"File not found: {file_path}"}),
                    )
                ]

            filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
            result = await use_case.execute(
                landscape_id=arguments["landscape_id"],
                file_bytes=file_bytes,
                filename=filename,
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="abap://{landscape_id}/objects",
                name="Analyzed Objects",
                description="List all analyzed ABAP custom objects for a landscape",
                mimeType="application/json",
            ),
            Resource(
                uri="abap://{landscape_id}/remediations",
                name="Remediation Suggestions",
                description="List all remediation suggestions for a landscape",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        # Parse URI: abap://<landscape_id>/<resource_type>
        parts = str(uri).replace("abap://", "").split("/")
        if len(parts) < 2:
            return json.dumps({"error": "Invalid resource URI"})

        landscape_id = parts[0]
        resource_type = parts[1]

        if resource_type == "objects":
            object_repo = container.resolve("CustomObjectRepositoryPort")
            objects = await object_repo.list_by_landscape(landscape_id)
            data = []
            for obj in objects:
                effort = None
                if obj.complexity_score is not None:
                    effort = {
                        "points": obj.complexity_score.points,
                        "description": obj.complexity_score.description,
                    }
                data.append(
                    {
                        "id": obj.id,
                        "object_name": obj.object_name,
                        "object_type": obj.object_type.value,
                        "package_name": obj.package_name,
                        "domain": obj.domain.value,
                        "compatibility_status": obj.compatibility_status.value,
                        "remediation_status": obj.remediation_status.value,
                        "deprecated_apis": list(obj.deprecated_apis),
                        "effort": effort,
                    }
                )
            return json.dumps(data, indent=2)

        if resource_type == "remediations":
            object_repo = container.resolve("CustomObjectRepositoryPort")
            remediation_repo = container.resolve("RemediationRepositoryPort")

            objects = await object_repo.list_by_landscape(landscape_id)
            all_remediations: list[dict] = []
            for obj in objects:
                suggestions = await remediation_repo.get_by_object(obj.id)
                for s in suggestions:
                    all_remediations.append(
                        {
                            "id": s.id,
                            "object_id": s.object_id,
                            "issue_type": s.issue_type,
                            "deprecated_api": s.deprecated_api,
                            "suggested_replacement": s.suggested_replacement,
                            "confidence_score": s.confidence_score,
                            "status": s.status.value,
                            "reviewed_by": s.reviewed_by,
                        }
                    )
            return json.dumps(all_remediations, indent=2)

        return json.dumps({"error": f"Unknown resource type: {resource_type}"})

    return server
