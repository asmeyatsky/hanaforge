"""Benchmark ports — async persistence boundaries for migration benchmarking."""

from __future__ import annotations

from typing import Protocol

from domain.entities.benchmark_entry import BenchmarkEntry
from domain.value_objects.benchmark_types import BenchmarkCriteria, BenchmarkStatistics


class BenchmarkRepositoryPort(Protocol):
    """Port for persisting and querying migration benchmark data."""

    async def save(self, entry: BenchmarkEntry) -> None: ...

    async def find_similar(self, criteria: BenchmarkCriteria, limit: int = 10) -> list[BenchmarkEntry]: ...

    async def get_statistics(self, criteria: BenchmarkCriteria) -> BenchmarkStatistics: ...

    async def get_by_id(self, id: str) -> BenchmarkEntry | None: ...

    async def list_all(self) -> list[BenchmarkEntry]: ...
