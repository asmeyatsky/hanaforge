"""ListDataPipelinesQuery — pipelines registered for a programme."""

from __future__ import annotations

from application.dtos.hana_bq_dto import DataPipelineListResponse, DataPipelineResponse
from domain.ports.hana_bq_ports import DataPipelineRepositoryPort


class ListDataPipelinesQuery:
    def __init__(self, pipeline_repo: DataPipelineRepositoryPort) -> None:
        self._pipeline_repo = pipeline_repo

    async def execute(self, programme_id: str) -> DataPipelineListResponse:
        items = await self._pipeline_repo.list_by_programme(programme_id)
        return DataPipelineListResponse(
            pipelines=[DataPipelineResponse.from_entity(p) for p in items],
        )
