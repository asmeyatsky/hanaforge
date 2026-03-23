"""ListPipelineRunsQuery — historical runs for a pipeline."""

from __future__ import annotations

from application.dtos.hana_bq_dto import PipelineRunResponse
from domain.ports.hana_bq_ports import DataPipelineRepositoryPort, PipelineRunRepositoryPort


class ListPipelineRunsQuery:
    def __init__(
        self,
        run_repo: PipelineRunRepositoryPort,
        pipeline_repo: DataPipelineRepositoryPort,
    ) -> None:
        self._run_repo = run_repo
        self._pipeline_repo = pipeline_repo

    async def execute(self, programme_id: str, pipeline_id: str) -> list[PipelineRunResponse] | None:
        pipeline = await self._pipeline_repo.get_by_id(pipeline_id)
        if pipeline is None or pipeline.programme_id != programme_id:
            return None
        runs = await self._run_repo.list_by_pipeline(pipeline_id)
        runs_sorted = sorted(runs, key=lambda r: r.started_at, reverse=True)
        return [PipelineRunResponse.from_entity(r) for r in runs_sorted]
