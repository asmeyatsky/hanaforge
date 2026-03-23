"""Value objects for SAP HANA → BigQuery data pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReplicationMode(str, Enum):
    """How source data is kept in sync with BigQuery."""

    FULL = "full"
    INCREMENTAL = "incremental"
    CDC = "cdc"


class JobPhase(str, Enum):
    """Phases within a single table replication run."""

    PENDING = "pending"
    EXTRACT = "extract"
    STAGE = "stage"
    LOAD = "load"
    VALIDATE = "validate"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineRunStatus(str, Enum):
    """Overall status of a pipeline execution."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class TableMapping:
    """Maps one HANA table to one BigQuery table."""

    source_schema: str
    source_table: str
    target_dataset: str
    target_table: str
    incremental_column: str | None = None

    def __post_init__(self) -> None:
        for label, val in (
            ("source_schema", self.source_schema),
            ("source_table", self.source_table),
            ("target_dataset", self.target_dataset),
            ("target_table", self.target_table),
        ):
            if not val or not val.strip():
                raise ValueError(f"{label} must be non-empty")
        if self.incremental_column is not None and not self.incremental_column.strip():
            raise ValueError("incremental_column, if set, must be non-empty")
