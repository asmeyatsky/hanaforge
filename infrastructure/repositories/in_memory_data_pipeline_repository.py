"""In-memory DataPipeline repository (development)."""

from __future__ import annotations

from domain.entities.data_pipeline import DataPipeline
from domain.ports.hana_bq_ports import DataPipelineRepositoryPort


class InMemoryDataPipelineRepository(DataPipelineRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[str, DataPipeline] = {}

    async def save(self, pipeline: DataPipeline) -> None:
        self._by_id[pipeline.id] = pipeline

    async def get_by_id(self, pipeline_id: str) -> DataPipeline | None:
        return self._by_id.get(pipeline_id)

    async def list_by_programme(self, programme_id: str) -> list[DataPipeline]:
        return [p for p in self._by_id.values() if p.programme_id == programme_id]
