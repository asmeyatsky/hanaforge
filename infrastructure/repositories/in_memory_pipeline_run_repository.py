"""In-memory PipelineRun repository (development)."""

from __future__ import annotations

from domain.entities.pipeline_run import PipelineRun
from domain.ports.hana_bq_ports import PipelineRunRepositoryPort


class InMemoryPipelineRunRepository(PipelineRunRepositoryPort):
    def __init__(self) -> None:
        self._by_id: dict[str, PipelineRun] = {}

    async def save(self, run: PipelineRun) -> None:
        self._by_id[run.id] = run

    async def get_by_id(self, run_id: str) -> PipelineRun | None:
        return self._by_id.get(run_id)

    async def list_by_pipeline(self, pipeline_id: str) -> list[PipelineRun]:
        return [r for r in self._by_id.values() if r.pipeline_id == pipeline_id]
