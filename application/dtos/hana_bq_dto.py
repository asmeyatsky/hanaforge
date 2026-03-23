"""HTTP DTOs for HANA → BigQuery pipelines."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from domain.entities.data_pipeline import DataPipeline
from domain.entities.pipeline_run import PipelineRun, TableRunRecord
from domain.value_objects.hana_bq_types import JobPhase, PipelineRunStatus, ReplicationMode


class TableMappingRequest(BaseModel):
    source_schema: str
    source_table: str
    target_dataset: str
    target_table: str
    incremental_column: str | None = None


class CreateDataPipelineRequest(BaseModel):
    landscape_id: str
    name: str = Field(..., min_length=1)
    replication_mode: ReplicationMode = ReplicationMode.FULL
    table_mappings: list[TableMappingRequest] = Field(..., min_length=1)
    hana_connection_ref: str = "default"


class DataPipelineResponse(BaseModel):
    id: str
    programme_id: str
    landscape_id: str
    name: str
    replication_mode: ReplicationMode
    table_mappings: list[TableMappingRequest]
    hana_connection_ref: str
    created_at: datetime

    @classmethod
    def from_entity(cls, p: DataPipeline) -> DataPipelineResponse:
        mappings = [
            TableMappingRequest(
                source_schema=m.source_schema,
                source_table=m.source_table,
                target_dataset=m.target_dataset,
                target_table=m.target_table,
                incremental_column=m.incremental_column,
            )
            for m in p.table_mappings
        ]
        return cls(
            id=p.id,
            programme_id=p.programme_id,
            landscape_id=p.landscape_id,
            name=p.name,
            replication_mode=p.replication_mode,
            table_mappings=mappings,
            hana_connection_ref=p.hana_connection_ref,
            created_at=p.created_at,
        )


class DataPipelineListResponse(BaseModel):
    pipelines: list[DataPipelineResponse]


class TableRunRecordResponse(BaseModel):
    source_schema: str
    source_table: str
    target_dataset: str
    target_table: str
    phase_reached: JobPhase
    rows_extracted: int
    rows_loaded: int | None
    staging_uri: str | None
    bq_job_id: str | None
    error_message: str | None

    @classmethod
    def from_record(cls, r: TableRunRecord) -> TableRunRecordResponse:
        return cls(
            source_schema=r.source_schema,
            source_table=r.source_table,
            target_dataset=r.target_dataset,
            target_table=r.target_table,
            phase_reached=r.phase_reached,
            rows_extracted=r.rows_extracted,
            rows_loaded=r.rows_loaded,
            staging_uri=r.staging_uri,
            bq_job_id=r.bq_job_id,
            error_message=r.error_message,
        )


class PipelineRunResponse(BaseModel):
    id: str
    pipeline_id: str
    programme_id: str
    status: PipelineRunStatus
    started_at: datetime
    completed_at: datetime | None
    table_results: list[TableRunRecordResponse]

    @classmethod
    def from_entity(cls, run: PipelineRun) -> PipelineRunResponse:
        return cls(
            id=run.id,
            pipeline_id=run.pipeline_id,
            programme_id=run.programme_id,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            table_results=[TableRunRecordResponse.from_record(t) for t in run.table_results],
        )


class ValidatePipelineResponse(BaseModel):
    hana_reachable: bool
    message: str


class HanaConnectionParams(BaseModel):
    """Override default HANA connection values from the environment."""

    address: str | None = None
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None


class StartPipelineRunRequest(BaseModel):
    """Optional knobs for a run (v1: row limit for smoke tests)."""

    row_limit_per_table: int | None = Field(default=None, ge=1, le=1_000_000)


class StartPipelineRunBody(BaseModel):
    """JSON body for starting a run (row limits + optional HANA overrides)."""

    row_limit_per_table: int | None = Field(default=None, ge=1, le=1_000_000)
    hana_connection: HanaConnectionParams | None = None


class PipelineRunListResponse(BaseModel):
    runs: list[PipelineRunResponse]
