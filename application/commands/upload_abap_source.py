"""UploadABAPSourceUseCase — uploads and parses ABAP source ZIP files."""

from __future__ import annotations

import io
import uuid
import zipfile

from domain.entities.custom_object import CustomObject
from domain.ports import (
    CustomObjectRepositoryPort,
    FileStoragePort,
    LandscapeRepositoryPort,
)
from domain.value_objects.object_type import (
    ABAPObjectType,
    BusinessDomain,
    CompatibilityStatus,
    RemediationStatus,
)

# ---------------------------------------------------------------------------
# Lightweight ABAP ZIP parser
# ---------------------------------------------------------------------------

def _parse_abap_zip(file_bytes: bytes) -> list[dict]:
    """Extract ABAP file names and source code from a ZIP archive.

    Returns a list of dicts with keys: object_name, object_type, source_code.
    """
    objects: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
        for entry in zf.namelist():
            if entry.endswith("/"):
                continue  # skip directories

            name_lower = entry.lower()
            source_code = zf.read(entry).decode("utf-8", errors="replace")
            object_name = entry.rsplit("/", 1)[-1].rsplit(".", 1)[0]

            # Simple heuristic to classify ABAP object type by extension
            if name_lower.endswith(".prog.abap"):
                object_type = ABAPObjectType.PROGRAM
            elif name_lower.endswith(".fugr.abap"):
                object_type = ABAPObjectType.FUNCTION_MODULE
            elif name_lower.endswith(".clas.abap"):
                object_type = ABAPObjectType.CLASS
            elif name_lower.endswith(".intf.abap"):
                object_type = ABAPObjectType.INTERFACE
            elif name_lower.endswith(".incl.abap"):
                object_type = ABAPObjectType.INCLUDE
            elif name_lower.endswith(".tabl.xml"):
                object_type = ABAPObjectType.TABLE
            elif name_lower.endswith(".view.xml"):
                object_type = ABAPObjectType.VIEW
            elif name_lower.endswith(".enho.abap"):
                object_type = ABAPObjectType.ENHANCEMENT
            else:
                object_type = ABAPObjectType.PROGRAM

            objects.append(
                {
                    "object_name": object_name,
                    "object_type": object_type,
                    "source_code": source_code,
                }
            )
    return objects


class UploadABAPSourceUseCase:
    """Single-responsibility use case: upload ABAP source ZIP, parse, and persist objects."""

    def __init__(
        self,
        storage: FileStoragePort,
        landscape_repo: LandscapeRepositoryPort,
        object_repo: CustomObjectRepositoryPort,
    ) -> None:
        self._storage = storage
        self._landscape_repo = landscape_repo
        self._object_repo = object_repo

    async def execute(
        self,
        landscape_id: str,
        file_bytes: bytes,
        filename: str,
    ) -> dict:
        # 1. Validate that the landscape exists
        landscape = await self._landscape_repo.get_by_id(landscape_id)
        if landscape is None:
            raise ValueError(f"Landscape {landscape_id} not found")

        # 2. Upload ZIP to file storage
        storage_key = f"abap-source/{landscape_id}/{filename}"
        await self._storage.upload(storage_key, file_bytes)

        # 3. Parse ABAP objects from ZIP
        parsed_objects = _parse_abap_zip(file_bytes)

        # 4. Create CustomObject entities and persist in batch
        entities: list[CustomObject] = []
        for obj in parsed_objects:
            entity = CustomObject(
                id=str(uuid.uuid4()),
                landscape_id=landscape_id,
                object_type=obj["object_type"],
                object_name=obj["object_name"],
                package_name=obj.get("package_name", "ZUNKNOWN"),
                domain=BusinessDomain(obj.get("domain", "UNKNOWN")),
                complexity_score=None,
                compatibility_status=CompatibilityStatus.UNKNOWN,
                remediation_status=RemediationStatus.NOT_STARTED,
                source_code=obj["source_code"],
                deprecated_apis=(),
            )
            entities.append(entity)

        await self._object_repo.save_batch(entities)

        return {
            "landscape_id": landscape_id,
            "filename": filename,
            "storage_key": storage_key,
            "objects_parsed": len(entities),
        }
