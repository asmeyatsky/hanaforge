"""GetPipelineRunQuery — fetch one pipeline run."""

from __future__ import annotations

from application.dtos.hana_bq_dto import PipelineRunResponse
from domain.ports.hana_bq_ports import DataPipelineRepositoryPort, PipelineRunRepositoryPort


class GetPipelineRunQuery:
    def __init__(
        self,
        run_repo: PipelineRunRepositoryPort,
        pipeline_repo: DataPipelineRepositoryPort,
    ) -> None:
        self._run_repo = run_repo
        self._pipeline_repo = pipeline_repo

    async def execute(self, programme_id: str, pipeline_id: str, run_id: str) -> PipelineRunResponse | None:
        pipeline = await self._pipeline_repo.get_by_id(pipeline_id)
        if pipeline is None or pipeline.programme_id != programme_id:
            return None
        run = await self._run_repo.get_by_id(run_id)
        if run is None or run.pipeline_id != pipeline_id:
            return None
        return PipelineRunResponse.from_entity(run)
