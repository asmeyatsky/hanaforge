"""StartPipelineRunUseCase — extract from HANA, stage, load BigQuery, record results."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from application.dtos.hana_bq_dto import PipelineRunResponse, StartPipelineRunRequest
from domain.entities.pipeline_run import PipelineRun, TableRunRecord
from domain.ports.hana_bq_ports import (
    BigQueryAdminPort,
    DataPipelineRepositoryPort,
    HanaExtractPort,
    PipelineRunRepositoryPort,
    PipelineStagingPort,
)
from domain.value_objects.hana_bq_types import JobPhase, PipelineRunStatus, ReplicationMode, TableMapping


class StartPipelineRunUseCase:
    def __init__(
        self,
        pipeline_repo: DataPipelineRepositoryPort,
        run_repo: PipelineRunRepositoryPort,
        hana: HanaExtractPort,
        staging: PipelineStagingPort,
        bigquery: BigQueryAdminPort,
    ) -> None:
        self._pipeline_repo = pipeline_repo
        self._run_repo = run_repo
        self._hana = hana
        self._staging = staging
        self._bigquery = bigquery

    async def execute(
        self,
        programme_id: str,
        pipeline_id: str,
        connection_params: dict[str, Any],
        request: StartPipelineRunRequest | None = None,
    ) -> PipelineRunResponse:
        req = request or StartPipelineRunRequest()
        pipeline = await self._pipeline_repo.get_by_id(pipeline_id)
        if pipeline is None or pipeline.programme_id != programme_id:
            raise ValueError(f"Pipeline {pipeline_id!r} not found")
        if pipeline.replication_mode == ReplicationMode.CDC:
            raise ValueError("CDC replication is not implemented yet; use full or incremental mode.")

        run_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc)
        datasets = {m.target_dataset for m in pipeline.table_mappings}
        for ds in sorted(datasets):
            await self._bigquery.ensure_dataset_exists(ds, location=None)

        records: list[TableRunRecord] = []
        any_failed = False

        for idx, mapping in enumerate(pipeline.table_mappings):
            rec = self._initial_record(mapping)
            try:
                csv_bytes, row_count = await self._hana.extract_table_to_csv(
                    connection_params,
                    mapping.source_schema,
                    mapping.source_table,
                    limit_rows=req.row_limit_per_table,
                )
                staging_key = f"{idx:04d}_{mapping.target_table}.csv"
                uri = await self._staging.stage_csv(programme_id, run_id, staging_key, csv_bytes)
                job_id = await self._bigquery.load_csv_from_uri(
                    uri,
                    mapping.target_dataset,
                    mapping.target_table,
                )
                records.append(
                    TableRunRecord(
                        source_schema=mapping.source_schema,
                        source_table=mapping.source_table,
                        target_dataset=mapping.target_dataset,
                        target_table=mapping.target_table,
                        phase_reached=JobPhase.COMPLETED,
                        rows_extracted=row_count,
                        rows_loaded=row_count,
                        staging_uri=uri,
                        bq_job_id=job_id,
                        error_message=None,
                    )
                )
            except Exception as exc:  # noqa: BLE001 — surface per-table failure to API
                any_failed = True
                records.append(
                    TableRunRecord(
                        source_schema=mapping.source_schema,
                        source_table=mapping.source_table,
                        target_dataset=mapping.target_dataset,
                        target_table=mapping.target_table,
                        phase_reached=JobPhase.FAILED,
                        rows_extracted=rec.rows_extracted,
                        rows_loaded=None,
                        staging_uri=None,
                        bq_job_id=None,
                        error_message=str(exc),
                    )
                )

        completed = datetime.now(timezone.utc)
        status = PipelineRunStatus.FAILED if any_failed else PipelineRunStatus.COMPLETED
        run = PipelineRun(
            id=run_id,
            pipeline_id=pipeline_id,
            programme_id=programme_id,
            status=status,
            started_at=started,
            completed_at=completed,
            table_results=tuple(records),
        )
        await self._run_repo.save(run)
        return PipelineRunResponse.from_entity(run)

    @staticmethod
    def _initial_record(mapping: TableMapping) -> TableRunRecord:
        return TableRunRecord(
            source_schema=mapping.source_schema,
            source_table=mapping.source_table,
            target_dataset=mapping.target_dataset,
            target_table=mapping.target_table,
            phase_reached=JobPhase.PENDING,
            rows_extracted=0,
            rows_loaded=None,
            staging_uri=None,
            bq_job_id=None,
            error_message=None,
        )
