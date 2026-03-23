"""BigQuery load jobs from GCS URIs."""

from __future__ import annotations

import asyncio

from google.api_core.exceptions import NotFound
from google.cloud import bigquery


class BigQueryAdminAdapter:
    def __init__(self, project_id: str, default_location: str = "US") -> None:
        self._project_id = project_id
        self._default_location = default_location

    async def ensure_dataset_exists(self, dataset_id: str, *, location: str | None = None) -> None:
        loc = location or self._default_location
        client = bigquery.Client(project=self._project_id)

        def _ensure() -> None:
            ds_ref = f"{self._project_id}.{dataset_id}"
            try:
                client.get_dataset(ds_ref)
            except NotFound:
                ds = bigquery.Dataset(ds_ref)
                ds.location = loc
                client.create_dataset(ds)

        await asyncio.to_thread(_ensure)

    async def load_csv_from_uri(
        self,
        staging_uri: str,
        dataset_id: str,
        table_id: str,
        *,
        write_disposition: str = "WRITE_TRUNCATE",
    ) -> str:
        if not staging_uri.startswith("gs://"):
            raise ValueError(
                "Real BigQuery loads require a gs:// URI. "
                "Configure HANAFORGE_GCS_BUCKET and use GcsPipelineStagingAdapter."
            )

        client = bigquery.Client(project=self._project_id)
        table_ref = f"{self._project_id}.{dataset_id}.{table_id}"

        disposition = (
            bigquery.WriteDisposition.WRITE_TRUNCATE
            if write_disposition == "WRITE_TRUNCATE"
            else bigquery.WriteDisposition.WRITE_APPEND
        )
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition=disposition,
        )

        def _run_load() -> str:
            job = client.load_table_from_uri(staging_uri, table_ref, job_config=job_config)
            job.result()
            jid = job.job_id
            if not isinstance(jid, str):
                raise TypeError(f"BigQuery job_id must be str, got {type(jid).__name__}")
            return jid

        return await asyncio.to_thread(_run_load)
