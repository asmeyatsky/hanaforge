"""DiscoveryWorkflow — DAG-orchestrated SAP landscape discovery.

Steps:
  connect ──┬── extract_metadata ──┐
            ├── extract_objects ────┤── score_complexity ── recommend_approach
            └── extract_integrations┘

extract_metadata, extract_objects, and extract_integrations run in PARALLEL.
"""

from __future__ import annotations

from typing import Any

from application.orchestration.dag_orchestrator import DAGOrchestrator, WorkflowStep
from domain.ports import (
    MigrationAdvisorPort,
    SAPDiscoveryPort,
)
from domain.services import ComplexityScoringService


class DiscoveryWorkflow:
    """Orchestrates the full SAP discovery process using a DAG of steps."""

    def __init__(
        self,
        sap_discovery: SAPDiscoveryPort,
        complexity_service: ComplexityScoringService,
        migration_advisor: MigrationAdvisorPort,
    ) -> None:
        self._sap_discovery = sap_discovery
        self._complexity_service = complexity_service
        self._migration_advisor = migration_advisor

    def _build_dag(self) -> DAGOrchestrator:
        steps = [
            WorkflowStep(
                name="connect",
                execute=self._connect,
                depends_on=[],
            ),
            WorkflowStep(
                name="extract_metadata",
                execute=self._extract_metadata,
                depends_on=["connect"],
            ),
            WorkflowStep(
                name="extract_objects",
                execute=self._extract_objects,
                depends_on=["connect"],
            ),
            WorkflowStep(
                name="extract_integrations",
                execute=self._extract_integrations,
                depends_on=["connect"],
            ),
            WorkflowStep(
                name="score_complexity",
                execute=self._score_complexity,
                depends_on=["extract_objects", "extract_integrations"],
            ),
            WorkflowStep(
                name="recommend_approach",
                execute=self._recommend_approach,
                depends_on=["score_complexity"],
            ),
        ]
        return DAGOrchestrator(steps)

    async def run(self, connection_params: dict) -> dict[str, Any]:
        """Execute the full discovery workflow, returning all step results."""
        dag = self._build_dag()
        return await dag.run(context={"connection_params": connection_params})

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    async def _connect(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:
        """Establish connection to the SAP system."""
        connection_params = context["connection_params"]
        connection = await self._sap_discovery.connect(connection_params)
        return connection

    async def _extract_metadata(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> dict:
        """Extract landscape metadata (system info, DB size, etc.)."""
        connection = results["connect"]
        metadata = await self._sap_discovery.extract_landscape_metadata(connection)
        return metadata

    async def _extract_objects(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict]:
        """Extract custom ABAP objects from the connected SAP system."""
        connection = results["connect"]
        objects = await self._sap_discovery.extract_custom_objects(connection)
        return objects

    async def _extract_integrations(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict]:
        """Extract integration points (RFC, IDocs, BAPIs, etc.)."""
        connection = results["connect"]
        integrations = await self._sap_discovery.extract_integration_points(connection)
        return integrations

    async def _score_complexity(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> dict:
        """Calculate the overall complexity score from objects and integrations."""
        objects = results["extract_objects"]
        integrations = results["extract_integrations"]
        score = await self._complexity_service.calculate(
            custom_objects=objects,
            integration_points=integrations,
        )
        return {
            "score": score.score,
            "risk_level": score.risk_level,
            "benchmark_percentile": score.benchmark_percentile,
        }

    async def _recommend_approach(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> dict:
        """Use AI to recommend a migration approach based on complexity analysis."""
        complexity = results["score_complexity"]
        metadata = results.get("extract_metadata", {})
        objects = results.get("extract_objects", [])

        landscape_summary = {
            "complexity_score": complexity,
            "metadata": metadata,
            "custom_objects_count": len(objects),
        }
        recommendation = await self._migration_advisor.recommend_approach(
            landscape_summary=landscape_summary,
        )
        return {
            "approach": recommendation.approach.value,
            "confidence": recommendation.confidence,
            "reasoning": recommendation.reasoning,
        }
