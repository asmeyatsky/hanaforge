"""Ports for SAP HANA extraction, staging, BigQuery load, and pipeline persistence."""

from __future__ import annotations

from typing import Any, Protocol

from domain.entities.data_pipeline import DataPipeline
from domain.entities.pipeline_run import PipelineRun


class HanaExtractPort(Protocol):
    """Extract relational data from SAP HANA as CSV bytes."""

    async def test_connection(self, connection_params: dict[str, Any]) -> bool:
        """Return True if credentials and network reach HANA."""
        ...

    async def extract_table_to_csv(
        self,
        connection_params: dict[str, Any],
        schema: str,
        table: str,
        *,
        limit_rows: int | None = None,
    ) -> tuple[bytes, int]:
        """Return UTF-8 CSV (including header) and logical row count excluding header."""
        ...


class PipelineStagingPort(Protocol):
    """Stage extracted files for BigQuery load (GCS or local dev URI)."""

    async def stage_csv(
        self,
        programme_id: str,
        run_id: str,
        relative_key: str,
        csv_bytes: bytes,
    ) -> str:
        """Upload CSV and return a URI meaningful to BigQueryAdminPort (e.g. gs://…)."""
        ...


class BigQueryAdminPort(Protocol):
    """Create datasets and load staged CSV into BigQuery tables."""

    async def ensure_dataset_exists(self, dataset_id: str, *, location: str | None = None) -> None:
        """Idempotently ensure the dataset exists."""
        ...

    async def load_csv_from_uri(
        self,
        staging_uri: str,
        dataset_id: str,
        table_id: str,
        *,
        write_disposition: str = "WRITE_TRUNCATE",
    ) -> str:
        """Start load job from staging URI; return job identifier (or synthetic id for stubs)."""
        ...


class DataPipelineRepositoryPort(Protocol):
    async def save(self, pipeline: DataPipeline) -> None: ...
    async def get_by_id(self, pipeline_id: str) -> DataPipeline | None: ...
    async def list_by_programme(self, programme_id: str) -> list[DataPipeline]: ...


class PipelineRunRepositoryPort(Protocol):
    async def save(self, run: PipelineRun) -> None: ...
    async def get_by_id(self, run_id: str) -> PipelineRun | None: ...
    async def list_by_pipeline(self, pipeline_id: str) -> list[PipelineRun]: ...
