"""Stage CSV extracts for BigQuery load (local filesystem or GCS)."""

from __future__ import annotations

import asyncio

from domain.ports.storage_ports import FileStoragePort


class LocalPipelineStagingAdapter:
    """Writes to FileStoragePort and returns a sentinel URI consumed by stub BigQuery."""

    def __init__(self, storage: FileStoragePort) -> None:
        self._storage = storage

    async def stage_csv(
        self,
        programme_id: str,
        run_id: str,
        relative_key: str,
        csv_bytes: bytes,
    ) -> str:
        key = f"hana-bq/{programme_id}/{run_id}/{relative_key}"
        await self._storage.upload(key, csv_bytes)
        return f"hanaforge-local://{key}"


class GcsPipelineStagingAdapter:
    """Uploads bytes to a GCS bucket and returns a gs:// URI for BigQuery load jobs."""

    def __init__(self, project_id: str, bucket_name: str) -> None:
        self._project_id = project_id
        self._bucket_name = bucket_name

    async def stage_csv(
        self,
        programme_id: str,
        run_id: str,
        relative_key: str,
        csv_bytes: bytes,
    ) -> str:
        from google.cloud import storage

        blob_path = f"hana-bq/{programme_id}/{run_id}/{relative_key}"

        def _upload() -> None:
            client = storage.Client(project=self._project_id)
            bucket = client.bucket(self._bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(csv_bytes, content_type="text/csv")

        await asyncio.to_thread(_upload)
        return f"gs://{self._bucket_name}/{blob_path}"
