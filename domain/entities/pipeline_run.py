"""PipelineRun — execution record for a HANA → BigQuery pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.value_objects.hana_bq_types import JobPhase, PipelineRunStatus


@dataclass(frozen=True)
class TableRunRecord:
    """Per-table outcome for one pipeline run."""

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


@dataclass(frozen=True)
class PipelineRun:
    """Single execution of a DataPipeline."""

    id: str
    pipeline_id: str
    programme_id: str
    status: PipelineRunStatus
    started_at: datetime
    completed_at: datetime | None
    table_results: tuple[TableRunRecord, ...]
