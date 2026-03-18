"""MCP server for GCP Infrastructure Provisioner (Module 05).

Exposes SAP on GCP infrastructure planning, Terraform generation, cost estimation,
and plan validation as MCP tools and resources. AI agents use these capabilities
to create and manage GCP landing zones for SAP S/4HANA migrations.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from infrastructure.config.dependency_injection import Container


def create_gcp_provisioner_server(container: Container) -> Server:
    """Build and return an MCP Server wired to GCP infrastructure use cases."""

    server = Server("hanaforge-gcp-provisioner")

    # ------------------------------------------------------------------
    # Tools — write operations (commands)
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="create_plan",
                description=(
                    "Create a GCP infrastructure plan for SAP S/4HANA. "
                    "Accepts sizing parameters (SAPS rating, memory, DB size, users) "
                    "and generates optimal HANA + app server configurations with "
                    "cost estimates."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "programme_id": {
                            "type": "string",
                            "description": "ID of the migration programme",
                        },
                        "sizing": {
                            "type": "object",
                            "description": "SAP sizing parameters",
                            "properties": {
                                "saps_rating": {"type": "integer"},
                                "hana_memory_gb": {"type": "integer"},
                                "db_size_gb": {"type": "number"},
                                "concurrent_users": {"type": "integer"},
                                "landscape_type": {
                                    "type": "string",
                                    "enum": ["DEV", "QAS", "PRD"],
                                },
                            },
                            "required": [
                                "saps_rating",
                                "hana_memory_gb",
                                "db_size_gb",
                                "concurrent_users",
                                "landscape_type",
                            ],
                        },
                        "region": {
                            "type": "string",
                            "description": "GCP region (e.g. us-central1, europe-west3)",
                        },
                        "ha_enabled": {
                            "type": "boolean",
                            "description": "Enable HA with Pacemaker clustering",
                            "default": True,
                        },
                        "dr_enabled": {
                            "type": "boolean",
                            "description": "Enable cross-region disaster recovery",
                            "default": False,
                        },
                        "dr_region": {
                            "type": "string",
                            "description": "DR region (required if dr_enabled is true)",
                        },
                    },
                    "required": ["programme_id", "sizing", "region"],
                },
            ),
            Tool(
                name="generate_terraform",
                description=(
                    "Generate complete Terraform HCL for a previously created "
                    "infrastructure plan. Produces production-grade HCL for VPC, "
                    "compute, storage, monitoring, and security."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plan_id": {
                            "type": "string",
                            "description": "ID of the infrastructure plan",
                        },
                    },
                    "required": ["plan_id"],
                },
            ),
            Tool(
                name="estimate_costs",
                description=(
                    "Calculate monthly GCP cost estimate for a programme's "
                    "infrastructure plan including CUD discount optimisation."
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
                name="validate_plan",
                description=(
                    "Validate an infrastructure plan against SAP on GCP "
                    "certification requirements. Returns passed/failed checks "
                    "and warnings."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plan_id": {
                            "type": "string",
                            "description": "ID of the infrastructure plan",
                        },
                    },
                    "required": ["plan_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "create_plan":
            from application.commands.create_infrastructure_plan import (
                CreateInfrastructurePlanUseCase,
            )
            from application.dtos.infrastructure_dto import (
                CreateInfrastructurePlanRequest,
                SizingInputRequest,
            )

            sizing_data = arguments["sizing"]
            request = CreateInfrastructurePlanRequest(
                sizing_input=SizingInputRequest(**sizing_data),
                region=arguments["region"],
                ha_enabled=arguments.get("ha_enabled", True),
                dr_enabled=arguments.get("dr_enabled", False),
                dr_region=arguments.get("dr_region"),
            )

            use_case: CreateInfrastructurePlanUseCase = container.resolve(
                "CreateInfrastructurePlanUseCase"
            )
            result = await use_case.execute(
                programme_id=arguments["programme_id"],
                request=request,
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "generate_terraform":

            use_case = container.resolve("GenerateTerraformUseCase")
            result = await use_case.execute(plan_id=arguments["plan_id"])
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "estimate_costs":

            use_case = container.resolve("EstimateCostsUseCase")
            result = await use_case.execute(
                programme_id=arguments["programme_id"]
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "validate_plan":
            from domain.services.plan_validation_service import (
                PlanValidationService,
            )

            repo = container.resolve("InfrastructurePlanRepositoryPort")
            plan = await repo.get_by_id(arguments["plan_id"])
            if plan is None:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": "Plan not found"}),
                    )
                ]

            validation_service = PlanValidationService()
            result = validation_service.validate_sap_certification(plan)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": result.status.value,
                            "checks_passed": result.checks_passed,
                            "checks_failed": result.checks_failed,
                            "warnings": list(result.warnings),
                            "errors": list(result.errors),
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
    # Resources — read operations (queries)
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="infra://{programme_id}/plan",
                name="Infrastructure Plan",
                description="Read the current infrastructure plan for a programme",
                mimeType="application/json",
            ),
            Resource(
                uri="infra://{programme_id}/terraform",
                name="Terraform HCL",
                description="Read the generated Terraform HCL for a programme",
                mimeType="text/plain",
            ),
            Resource(
                uri="infra://{programme_id}/costs",
                name="Cost Estimate",
                description="Read the cost estimate for a programme",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        parts = str(uri).replace("infra://", "").split("/")
        if len(parts) < 2:
            return json.dumps({"error": "Invalid resource URI"})

        programme_id = parts[0]
        resource_type = parts[1]

        if resource_type == "plan":
            from application.queries.get_infrastructure_plan import (
                GetInfrastructurePlanQuery,
            )

            query: GetInfrastructurePlanQuery = container.resolve(
                "GetInfrastructurePlanQuery"
            )
            result = await query.execute(programme_id=programme_id)
            if result is None:
                return json.dumps({"error": "No plan found for this programme"})
            return result.model_dump_json(indent=2)

        if resource_type == "terraform":
            repo = container.resolve("InfrastructurePlanRepositoryPort")
            plan = await repo.get_latest_by_programme(programme_id)
            if plan is None or plan.terraform_plan_ref is None:
                return json.dumps(
                    {"error": "No Terraform plan generated for this programme"}
                )
            return json.dumps(
                {
                    "plan_ref": plan.terraform_plan_ref,
                    "status": plan.validation_status.value,
                    "message": "Use generate_terraform tool to regenerate HCL content",
                },
                indent=2,
            )

        if resource_type == "costs":
            from application.commands.estimate_costs import EstimateCostsUseCase

            try:
                use_case: EstimateCostsUseCase = container.resolve(
                    "EstimateCostsUseCase"
                )
                result = await use_case.execute(programme_id=programme_id)
                return result.model_dump_json(indent=2)
            except ValueError as exc:
                return json.dumps({"error": str(exc)})

        return json.dumps({"error": f"Unknown resource type: {resource_type}"})

    return server
