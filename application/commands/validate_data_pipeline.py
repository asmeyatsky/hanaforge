"""ValidateDataPipelineUseCase — connectivity check against SAP HANA."""

from __future__ import annotations

from application.dtos.hana_bq_dto import ValidatePipelineResponse
from domain.ports.hana_bq_ports import DataPipelineRepositoryPort, HanaExtractPort


class ValidateDataPipelineUseCase:
    def __init__(
        self,
        pipeline_repo: DataPipelineRepositoryPort,
        hana: HanaExtractPort,
    ) -> None:
        self._pipeline_repo = pipeline_repo
        self._hana = hana

    async def execute(
        self,
        programme_id: str,
        pipeline_id: str,
        connection_params: dict,
    ) -> ValidatePipelineResponse:
        pipeline = await self._pipeline_repo.get_by_id(pipeline_id)
        if pipeline is None or pipeline.programme_id != programme_id:
            raise ValueError(f"Pipeline {pipeline_id!r} not found")

        ok = await self._hana.test_connection(connection_params)
        if ok:
            return ValidatePipelineResponse(
                hana_reachable=True,
                message="SAP HANA accepted the supplied connection parameters.",
            )
        return ValidatePipelineResponse(
            hana_reachable=False,
            message="Could not reach SAP HANA with the supplied connection parameters.",
        )
