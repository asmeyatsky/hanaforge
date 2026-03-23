"""CreateDataPipelineUseCase — register a HANA → BigQuery pipeline for a programme."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from application.dtos.hana_bq_dto import CreateDataPipelineRequest, DataPipelineResponse
from domain.entities.data_pipeline import DataPipeline
from domain.ports.hana_bq_ports import DataPipelineRepositoryPort
from domain.ports.repository_ports import LandscapeRepositoryPort
from domain.value_objects.hana_bq_types import TableMapping


class CreateDataPipelineUseCase:
    def __init__(
        self,
        pipeline_repo: DataPipelineRepositoryPort,
        landscape_repo: LandscapeRepositoryPort,
    ) -> None:
        self._pipeline_repo = pipeline_repo
        self._landscape_repo = landscape_repo

    async def execute(self, programme_id: str, request: CreateDataPipelineRequest) -> DataPipelineResponse:
        landscape = await self._landscape_repo.get_by_id(request.landscape_id)
        if landscape is None:
            raise ValueError(f"Landscape {request.landscape_id!r} not found")
        if landscape.programme_id != programme_id:
            raise ValueError(f"Landscape {request.landscape_id!r} does not belong to this programme")

        mappings = tuple(
            TableMapping(
                source_schema=m.source_schema.strip(),
                source_table=m.source_table.strip(),
                target_dataset=m.target_dataset.strip(),
                target_table=m.target_table.strip(),
                incremental_column=m.incremental_column.strip() if m.incremental_column else None,
            )
            for m in request.table_mappings
        )

        now = datetime.now(timezone.utc)
        pipeline = DataPipeline(
            id=str(uuid.uuid4()),
            programme_id=programme_id,
            landscape_id=request.landscape_id,
            name=request.name.strip(),
            replication_mode=request.replication_mode,
            table_mappings=mappings,
            hana_connection_ref=request.hana_connection_ref.strip() or "default",
            created_at=now,
        )
        await self._pipeline_repo.save(pipeline)
        return DataPipelineResponse.from_entity(pipeline)
