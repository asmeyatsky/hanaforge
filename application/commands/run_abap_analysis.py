"""RunABAPAnalysisUseCase — AI-powered parallel analysis of ABAP custom objects."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from domain.entities.custom_object import CustomObject
from domain.entities.remediation import RemediationSuggestion
from domain.events.programme_events import AnalysisCompletedEvent
from domain.ports import (
    ABAPAnalysisPort,
    AnalysisResult,
    CustomObjectRepositoryPort,
    EventBusPort,
    RemediationRepositoryPort,
)
from domain.value_objects.object_type import (
    CompatibilityStatus,
    ReviewStatus,
)

from application.dtos.analysis_dto import ABAPAnalysisResponse, AnalysisResultsResponse


_MAX_CONCURRENT = 10


class RunABAPAnalysisUseCase:
    """Single-responsibility use case: run parallel AI analysis on all custom objects."""

    def __init__(
        self,
        object_repo: CustomObjectRepositoryPort,
        remediation_repo: RemediationRepositoryPort,
        ai_analysis: ABAPAnalysisPort,
        event_bus: EventBusPort,
    ) -> None:
        self._object_repo = object_repo
        self._remediation_repo = remediation_repo
        self._ai_analysis = ai_analysis
        self._event_bus = event_bus

    async def execute(
        self,
        landscape_id: str,
        programme_id: str,
    ) -> AnalysisResultsResponse:
        # 1. Load all custom objects for this landscape
        objects = await self._object_repo.get_by_landscape(landscape_id)
        if not objects:
            return AnalysisResultsResponse(
                programme_id=programme_id,
                total_objects=0,
                compatible_count=0,
                incompatible_count=0,
                needs_review_count=0,
                objects=[],
            )

        # 2. Parallel AI analysis with semaphore for rate limiting
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _analyse_one(obj: CustomObject) -> tuple[AnalysisResult, CustomObject]:
            async with semaphore:
                result = await self._ai_analysis.analyze_object(
                    source_code=obj.source_code,
                    object_type=obj.object_type,
                    sap_source_version="ECC 6.0",
                    target_version="S/4HANA 2023",
                )
                return result, obj

        analysis_tasks = [_analyse_one(obj) for obj in objects]
        analysis_outputs = await asyncio.gather(*analysis_tasks)

        # 3. Process results: update objects and create remediation suggestions
        updated_objects: list[CustomObject] = []
        remediation_suggestions: list[RemediationSuggestion] = []
        response_items: list[ABAPAnalysisResponse] = []

        compatible_count = 0
        incompatible_count = 0
        needs_review_count = 0

        for result, original_obj in analysis_outputs:
            status = CompatibilityStatus(result.compatibility_status)

            if status == CompatibilityStatus.COMPATIBLE:
                compatible_count += 1
            elif status == CompatibilityStatus.INCOMPATIBLE:
                incompatible_count += 1
            elif status == CompatibilityStatus.NEEDS_REVIEW:
                needs_review_count += 1

            # Create an updated CustomObject with analysis results
            updated_obj = CustomObject(
                id=original_obj.id,
                landscape_id=original_obj.landscape_id,
                object_type=original_obj.object_type,
                object_name=original_obj.object_name,
                package_name=original_obj.package_name,
                domain=original_obj.domain,
                complexity_score=original_obj.complexity_score,
                compatibility_status=status,
                remediation_status=original_obj.remediation_status,
                source_code=original_obj.source_code,
                deprecated_apis=tuple(result.deprecated_apis),
            )
            updated_objects.append(updated_obj)

            # Create remediation suggestion if the object is incompatible
            remediation_available = False
            if status == CompatibilityStatus.INCOMPATIBLE and result.suggested_replacement:
                suggestion = RemediationSuggestion(
                    id=str(uuid.uuid4()),
                    object_id=original_obj.id,
                    issue_type=result.issue_type or "deprecated_api",
                    deprecated_api=result.deprecated_api or "",
                    suggested_replacement=result.suggested_replacement,
                    generated_code=result.generated_code or "",
                    confidence_score=result.confidence_score,
                    reviewed_by=None,
                    status=ReviewStatus.PENDING,
                    created_at=datetime.now(timezone.utc),
                )
                remediation_suggestions.append(suggestion)
                remediation_available = True

            response_items.append(
                ABAPAnalysisResponse(
                    object_id=original_obj.id,
                    object_name=original_obj.object_name,
                    object_type=original_obj.object_type.value,
                    compatibility_status=status.value,
                    deprecated_apis=list(result.deprecated_apis),
                    effort_points=result.effort_points,
                    remediation_available=remediation_available,
                )
            )

        # 4. Persist all updates
        await self._object_repo.save_batch(updated_objects)
        if remediation_suggestions:
            await self._remediation_repo.save_batch(remediation_suggestions)

        # 5. Publish analysis completed event
        event = AnalysisCompletedEvent(
            aggregate_id=programme_id,
            compatible_count=compatible_count,
            incompatible_count=incompatible_count,
        )
        await self._event_bus.publish(event)

        return AnalysisResultsResponse(
            programme_id=programme_id,
            total_objects=len(objects),
            compatible_count=compatible_count,
            incompatible_count=incompatible_count,
            needs_review_count=needs_review_count,
            objects=response_items,
        )
