"""ExportRemediationBacklogUseCase — exports remediation backlog to project management formats."""

from __future__ import annotations

from domain.ports.remediation_export_ports import (
    RemediationExporterPort,
    RemediationExportFormat,
)
from domain.ports.repository_ports import (
    CustomObjectRepositoryPort,
    RemediationRepositoryPort,
)


class ExportRemediationBacklogUseCase:
    """Load all remediations for a landscape, sort by priority, and export."""

    def __init__(
        self,
        object_repo: CustomObjectRepositoryPort,
        remediation_repo: RemediationRepositoryPort,
        exporter: RemediationExporterPort,
    ) -> None:
        self._object_repo = object_repo
        self._remediation_repo = remediation_repo
        self._exporter = exporter

    async def execute(
        self,
        landscape_id: str,
        format: RemediationExportFormat,
    ) -> bytes:
        # 1. Load all custom objects for the landscape
        objects = await self._object_repo.get_by_landscape(landscape_id)

        if not objects:
            return await self._exporter.export_remediations([], [], format)

        # 2. Load all remediation suggestions for those objects
        object_ids = [obj.id for obj in objects]
        remediations = await self._remediation_repo.get_by_object_ids(object_ids)

        # 3. Build lookup for sorting
        obj_lookup = {obj.id: obj for obj in objects}

        # 4. Sort by priority: effort_points desc, then confidence_score desc
        def _sort_key(r):
            obj = obj_lookup.get(r.object_id)
            effort = obj.complexity_score.points if obj and obj.complexity_score else 0
            return (-effort, -r.confidence_score)

        remediations_sorted = sorted(remediations, key=_sort_key)

        # 5. Export
        return await self._exporter.export_remediations(
            remediations_sorted, objects, format
        )
