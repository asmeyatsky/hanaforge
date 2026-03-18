"""MCP server for Data Readiness Engine (Module 03).

Exposes data profiling, BP consolidation, and Universal Journal assessment
capabilities as MCP tools and resources, enabling AI agents to evaluate
data migration readiness.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from infrastructure.config.dependency_injection import Container


def create_data_readiness_server(container: Container) -> Server:
    """Build and return an MCP Server wired to the data readiness use cases."""

    server = Server("hanaforge-data-readiness")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="upload_data_export",
                description=(
                    "Upload an SAP table data export (CSV, XLSX, or LTMC XML) "
                    "for a landscape. The file is stored and a DataDomain stub "
                    "is created for subsequent profiling."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "landscape_id": {
                            "type": "string",
                            "description": "ID of the SAP landscape",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Local path to the data export file",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["csv", "xlsx", "xml"],
                            "description": "File format (csv, xlsx, or xml)",
                        },
                    },
                    "required": ["landscape_id", "file_path", "format"],
                },
            ),
            Tool(
                name="run_profiling",
                description=(
                    "Run data profiling on all uploaded tables for a landscape. "
                    "Calculates null rates, duplicate keys, referential integrity, "
                    "and encoding issues in parallel."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "landscape_id": {
                            "type": "string",
                            "description": "ID of the SAP landscape to profile",
                        },
                    },
                    "required": ["landscape_id"],
                },
            ),
            Tool(
                name="assess_bp_consolidation",
                description=(
                    "Assess Business Partner consolidation readiness by comparing "
                    "customer and vendor records to detect merge candidates."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "landscape_id": {
                            "type": "string",
                            "description": "ID of the SAP landscape",
                        },
                        "customer_file": {
                            "type": "string",
                            "description": "Path to the customer master data CSV file",
                        },
                        "vendor_file": {
                            "type": "string",
                            "description": "Path to the vendor master data CSV file",
                        },
                    },
                    "required": ["landscape_id", "customer_file", "vendor_file"],
                },
            ),
            Tool(
                name="assess_universal_journal",
                description=(
                    "Assess Universal Journal (ACDOCA) migration readiness by "
                    "evaluating FI and CO configurations for custom coding blocks, "
                    "profit centre assignments, and segment reporting."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "landscape_id": {
                            "type": "string",
                            "description": "ID of the SAP landscape",
                        },
                        "fi_config": {
                            "type": "object",
                            "description": "FI configuration dict",
                        },
                        "co_config": {
                            "type": "object",
                            "description": "CO configuration dict",
                        },
                    },
                    "required": ["landscape_id", "fi_config", "co_config"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "upload_data_export":
            use_case = container.resolve("UploadDataExportUseCase")

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
                format=arguments["format"],
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "run_profiling":
            use_case = container.resolve("RunDataProfilingUseCase")
            result = await use_case.execute(
                landscape_id=arguments["landscape_id"],
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "assess_bp_consolidation":
            use_case = container.resolve("AssessBPConsolidationUseCase")

            customer_path = arguments["customer_file"]
            vendor_path = arguments["vendor_file"]

            try:
                with open(customer_path, "rb") as f:
                    customer_bytes = f.read()
                with open(vendor_path, "rb") as f:
                    vendor_bytes = f.read()
            except FileNotFoundError as e:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"File not found: {e}"}),
                    )
                ]

            result = await use_case.execute(
                landscape_id=arguments["landscape_id"],
                customer_file_bytes=customer_bytes,
                vendor_file_bytes=vendor_bytes,
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "customer_count": result.customer_count,
                            "vendor_count": result.vendor_count,
                            "duplicate_pairs": result.duplicate_pairs,
                            "merge_candidates": len(result.merge_candidates),
                            "consolidation_complexity": result.consolidation_complexity,
                        },
                        indent=2,
                    ),
                )
            ]

        if name == "assess_universal_journal":
            use_case = container.resolve("AssessUniversalJournalUseCase")
            result = await use_case.execute(
                landscape_id=arguments["landscape_id"],
                fi_config=arguments["fi_config"],
                co_config=arguments["co_config"],
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "custom_coding_blocks": list(result.custom_coding_blocks),
                            "profit_centre_assignments": result.profit_centre_assignments,
                            "segment_reporting_configs": result.segment_reporting_configs,
                            "fi_gl_simplification_impact": result.fi_gl_simplification_impact,
                            "migration_complexity": result.migration_complexity,
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
                uri="data://{landscape_id}/profiles",  # type: ignore[arg-type]
                name="Data Profiles",
                description="Read data profiling results for a landscape",
                mimeType="application/json",
            ),
            Resource(
                uri="data://{landscape_id}/risk-register",  # type: ignore[arg-type]
                name="Risk Register",
                description="Read data migration risk register for a landscape",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        # Parse URI: data://<landscape_id>/<resource_type>
        parts = str(uri).replace("data://", "").split("/")
        if len(parts) < 2:
            return json.dumps({"error": "Invalid resource URI"})

        landscape_id = parts[0]
        resource_type = parts[1]

        if resource_type == "profiles":
            query = container.resolve("GetDataProfilingResultsQuery")
            result = await query.execute(landscape_id=landscape_id)
            return str(result.model_dump_json(indent=2))

        if resource_type == "risk-register":
            query = container.resolve("GetDataProfilingResultsQuery")
            result = await query.execute(landscape_id=landscape_id)
            return json.dumps(result.risk_register, indent=2)

        return json.dumps({"error": f"Unknown resource type: {resource_type}"})

    return server
