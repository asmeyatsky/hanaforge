"""GetAnalysisResultsQuery — retrieves analysis results for a programme landscape."""

from __future__ import annotations

from domain.ports import CustomObjectRepositoryPort, RemediationRepositoryPort
from domain.value_objects.object_type import CompatibilityStatus

from application.dtos.analysis_dto import ABAPAnalysisResponse, AnalysisResultsResponse


class GetAnalysisResultsQuery:
    """Read-only query: fetch analysis results for all objects in a landscape."""

    def __init__(
        self,
        object_repo: CustomObjectRepositoryPort,
        remediation_repo: RemediationRepositoryPort,
    ) -> None:
        self._object_repo = object_repo
        self._remediation_repo = remediation_repo

    async def execute(
        self,
        programme_id: str,
        landscape_id: str,
    ) -> AnalysisResultsResponse:
        objects = await self._object_repo.get_by_landscape(landscape_id)

        # Collect all object IDs that have remediation suggestions
        object_ids = [obj.id for obj in objects]
        remediations = await self._remediation_repo.get_by_object_ids(object_ids)
        remediation_object_ids: set[str] = {r.object_id for r in remediations}

        compatible_count = 0
        incompatible_count = 0
        needs_review_count = 0
        response_items: list[ABAPAnalysisResponse] = []

        for obj in objects:
            if obj.compatibility_status == CompatibilityStatus.COMPATIBLE:
                compatible_count += 1
            elif obj.compatibility_status == CompatibilityStatus.INCOMPATIBLE:
                incompatible_count += 1
            elif obj.compatibility_status == CompatibilityStatus.NEEDS_REVIEW:
                needs_review_count += 1

            response_items.append(
                ABAPAnalysisResponse(
                    object_id=obj.id,
                    object_name=obj.object_name,
                    object_type=obj.object_type.value,
                    compatibility_status=obj.compatibility_status.value,
                    deprecated_apis=list(obj.deprecated_apis),
                    effort_points=None,
                    remediation_available=obj.id in remediation_object_ids,
                )
            )

        return AnalysisResultsResponse(
            programme_id=programme_id,
            total_objects=len(objects),
            compatible_count=compatible_count,
            incompatible_count=incompatible_count,
            needs_review_count=needs_review_count,
            objects=response_items,
        )
