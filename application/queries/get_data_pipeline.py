"""GetDataPipelineQuery — fetch a single pipeline by id."""

from __future__ import annotations

from application.dtos.hana_bq_dto import DataPipelineResponse
from domain.ports.hana_bq_ports import DataPipelineRepositoryPort


class GetDataPipelineQuery:
    def __init__(self, pipeline_repo: DataPipelineRepositoryPort) -> None:
        self._pipeline_repo = pipeline_repo

    async def execute(self, programme_id: str, pipeline_id: str) -> DataPipelineResponse | None:
        p = await self._pipeline_repo.get_by_id(pipeline_id)
        if p is None or p.programme_id != programme_id:
            return None
        return DataPipelineResponse.from_entity(p)
