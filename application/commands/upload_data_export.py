"""UploadDataExportUseCase — uploads SAP table data exports (CSV/XLSX/XML)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.entities.data_domain import DataDomain
from domain.ports.data_analysis_ports import DataRepositoryPort
from domain.ports.event_bus_ports import EventBusPort
from domain.ports.repository_ports import LandscapeRepositoryPort
from domain.ports.storage_ports import FileStoragePort
from domain.value_objects.data_quality import DataMigrationStatus


class UploadDataExportUseCase:
    """Single-responsibility use case: accept SAP table data exports and create DataDomain stubs."""

    def __init__(
        self,
        storage: FileStoragePort,
        landscape_repo: LandscapeRepositoryPort,
        data_repo: DataRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._storage = storage
        self._landscape_repo = landscape_repo
        self._data_repo = data_repo
        self._event_bus = event_bus

    async def execute(
        self,
        landscape_id: str,
        file_bytes: bytes,
        filename: str,
        format: str,
    ) -> dict:
        # 1. Validate landscape exists
        landscape = await self._landscape_repo.get_by_id(landscape_id)
        if landscape is None:
            raise ValueError(f"Landscape {landscape_id} not found")

        # 2. Validate format
        supported_formats = ("csv", "xlsx", "xml")
        if format.lower() not in supported_formats:
            raise ValueError(f"Unsupported format {format!r}; must be one of {supported_formats}")

        # 3. Upload to file storage
        storage_key = f"data-exports/{landscape_id}/{filename}"
        await self._storage.upload(storage_key, file_bytes)

        # 4. Derive table name from filename
        table_name = filename.rsplit(".", 1)[0].upper()

        # 5. Create DataDomain entity stub
        domain_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        data_domain = DataDomain(
            id=domain_id,
            landscape_id=landscape_id,
            table_name=table_name,
            record_count=0,
            field_count=0,
            null_rates=(),
            duplicate_key_count=0,
            referential_integrity_score=0.0,
            encoding_issues=(),
            migration_status=DataMigrationStatus.NOT_PROFILED,
            transformation_rules=(),
            quality_score=None,
            created_at=now,
        )

        await self._data_repo.save(data_domain)

        return {
            "data_domain_id": domain_id,
            "landscape_id": landscape_id,
            "table_name": table_name,
            "filename": filename,
            "format": format,
            "storage_key": storage_key,
        }
