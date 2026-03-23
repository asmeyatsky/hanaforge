"""DataPipeline aggregate — HANA → BigQuery replication definition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.value_objects.hana_bq_types import ReplicationMode, TableMapping


@dataclass(frozen=True)
class DataPipeline:
    """Configured path from SAP HANA tables into BigQuery."""

    id: str
    programme_id: str
    landscape_id: str
    name: str
    replication_mode: ReplicationMode
    table_mappings: tuple[TableMapping, ...]
    hana_connection_ref: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.table_mappings:
            raise ValueError("at least one table mapping is required")
