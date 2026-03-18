"""Data analysis ports — boundaries for data profiling and transformation infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.entities.data_domain import DataDomain
from domain.value_objects.data_quality import FieldNullRate, TransformationRule


@dataclass(frozen=True)
class ProfileResult:
    """Result of profiling a single table dataset."""

    record_count: int
    field_count: int
    null_rates: tuple[FieldNullRate, ...]
    duplicate_keys: int
    encoding_issues: tuple[str, ...]


class DataProfilingPort(Protocol):
    async def profile_table(self, table_data: bytes, format: str) -> ProfileResult: ...


class DataTransformationPort(Protocol):
    async def generate_rules(
        self,
        source_schema: dict,
        target_schema: dict,
        sample_data: list[dict],
    ) -> list[TransformationRule]: ...


class DataRepositoryPort(Protocol):
    async def save(self, data_domain: DataDomain) -> None: ...
    async def get_by_id(self, id: str) -> DataDomain | None: ...
    async def list_by_landscape(self, landscape_id: str) -> list[DataDomain]: ...
    async def get_by_table_name(self, landscape_id: str, table_name: str) -> DataDomain | None: ...
