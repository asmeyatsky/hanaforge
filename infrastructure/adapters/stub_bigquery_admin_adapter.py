"""Stub BigQuery admin — simulates dataset creation and load jobs (local dev)."""

from __future__ import annotations

import uuid


class StubBigQueryAdminAdapter:
    async def ensure_dataset_exists(self, dataset_id: str, *, location: str | None = None) -> None:
        _ = dataset_id
        _ = location

    async def load_csv_from_uri(
        self,
        staging_uri: str,
        dataset_id: str,
        table_id: str,
        *,
        write_disposition: str = "WRITE_TRUNCATE",
    ) -> str:
        _ = write_disposition
        _ = dataset_id
        _ = table_id
        if not staging_uri:
            raise ValueError("staging_uri is required")
        return f"stub-load-job-{uuid.uuid4().hex[:12]}"
