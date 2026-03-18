"""ABAPAnalysisWorkflow — DAG-orchestrated ABAP compatibility analysis.

Steps:
  load_objects ── analyze_compatibility ── generate_remediations ── prioritize_backlog ── publish_results

analyze_compatibility runs AI analysis in parallel (semaphore-gated).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from application.orchestration.dag_orchestrator import DAGOrchestrator, WorkflowStep
from domain.entities.remediation import RemediationSuggestion
from domain.events.programme_events import AnalysisCompletedEvent
from domain.ports import (
    ABAPAnalysisPort,
    CustomObjectRepositoryPort,
    EventBusPort,
    RemediationRepositoryPort,
)
from domain.services import RemediationPriorityService
from domain.value_objects.object_type import CompatibilityStatus, RemediationStatus

_MAX_CONCURRENT = 10


class ABAPAnalysisWorkflow:
    """Orchestrates end-to-end ABAP analysis using a DAG of steps."""

    def __init__(
        self,
        object_repo: CustomObjectRepositoryPort,
        remediation_repo: RemediationRepositoryPort,
        ai_analysis: ABAPAnalysisPort,
        priority_service: RemediationPriorityService,
        event_bus: EventBusPort,
    ) -> None:
        self._object_repo = object_repo
        self._remediation_repo = remediation_repo
        self._ai_analysis = ai_analysis
        self._priority_service = priority_service
        self._event_bus = event_bus

    def _build_dag(self) -> DAGOrchestrator:
        steps = [
            WorkflowStep(
                name="load_objects",
                execute=self._load_objects,
                depends_on=[],
            ),
            WorkflowStep(
                name="analyze_compatibility",
                execute=self._analyze_compatibility,
                depends_on=["load_objects"],
            ),
            WorkflowStep(
                name="generate_remediations",
                execute=self._generate_remediations,
                depends_on=["analyze_compatibility"],
            ),
            WorkflowStep(
                name="prioritize_backlog",
                execute=self._prioritize_backlog,
                depends_on=["generate_remediations"],
            ),
            WorkflowStep(
                name="publish_results",
                execute=self._publish_results,
                depends_on=["prioritize_backlog"],
            ),
        ]
        return DAGOrchestrator(steps)

    async def run(self, landscape_id: str, programme_id: str) -> dict[str, Any]:
        """Execute the full ABAP analysis workflow."""
        dag = self._build_dag()
        return await dag.run(
            context={
                "landscape_id": landscape_id,
                "programme_id": programme_id,
            }
        )

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    async def _load_objects(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> list:
        """Fetch all custom objects for the landscape from the repository."""
        landscape_id = context["landscape_id"]
        objects = await self._object_repo.get_by_landscape(landscape_id)
        return objects

    async def _analyze_compatibility(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict]:
        """Run AI-powered compatibility analysis on all objects in parallel."""
        objects = results["load_objects"]
        if not objects:
            return []

        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _analyse_one(obj: Any) -> dict:
            async with semaphore:
                result = await self._ai_analysis.analyse(obj)
                return {
                    "object": obj,
                    "result": result,
                }

        tasks = [_analyse_one(obj) for obj in objects]
        return await asyncio.gather(*tasks)

    async def _generate_remediations(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> list[RemediationSuggestion]:
        """Create RemediationSuggestion entities for incompatible objects."""
        analysis_outputs = results["analyze_compatibility"]
        suggestions: list[RemediationSuggestion] = []

        for item in analysis_outputs:
            result = item["result"]
            original_obj = item["object"]

            status = CompatibilityStatus(result.compatibility_status)
            if status != CompatibilityStatus.INCOMPATIBLE:
                continue
            if not result.suggested_replacement:
                continue

            suggestion = RemediationSuggestion(
                id=str(uuid.uuid4()),
                object_id=original_obj.id,
                issue_type=result.issue_type or "deprecated_api",
                deprecated_api=result.deprecated_api or "",
                suggested_replacement=result.suggested_replacement,
                generated_code=result.generated_code or "",
                confidence_score=result.confidence_score,
                status=RemediationStatus.NOT_STARTED,
            )
            suggestions.append(suggestion)

        return suggestions

    async def _prioritize_backlog(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> list[RemediationSuggestion]:
        """Sort remediation suggestions by priority using the domain service."""
        suggestions = results["generate_remediations"]
        if not suggestions:
            return []

        prioritized = await self._priority_service.prioritize(suggestions)
        return prioritized

    async def _publish_results(
        self,
        results: dict[str, Any],
        context: dict[str, Any],
    ) -> dict:
        """Persist all remediation suggestions and publish completion event."""
        prioritized = results["prioritize_backlog"]
        analysis_outputs = results["analyze_compatibility"]
        programme_id = context["programme_id"]

        # Persist remediations
        if prioritized:
            await self._remediation_repo.save_batch(prioritized)

        # Count results
        compatible = 0
        incompatible = 0
        for item in analysis_outputs:
            status = CompatibilityStatus(item["result"].compatibility_status)
            if status == CompatibilityStatus.COMPATIBLE:
                compatible += 1
            elif status == CompatibilityStatus.INCOMPATIBLE:
                incompatible += 1

        # Publish event
        event = AnalysisCompletedEvent(
            aggregate_id=programme_id,
            compatible_count=compatible,
            incompatible_count=incompatible,
        )
        await self._event_bus.publish(event)

        return {
            "programme_id": programme_id,
            "total_analysed": len(analysis_outputs),
            "compatible": compatible,
            "incompatible": incompatible,
            "remediations_created": len(prioritized),
        }
