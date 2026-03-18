"""InMemoryProgrammeRepository — dev-mode in-memory implementation of ProgrammeRepositoryPort.

A Firestore-backed implementation will replace this once GCP infrastructure is
provisioned.  The in-memory variant keeps the development loop fast and
dependency-free.
"""

from __future__ import annotations

from datetime import datetime

from domain.entities.programme import Programme
from domain.value_objects.complexity_score import ComplexityScore
from domain.value_objects.object_type import ProgrammeStatus


class InMemoryProgrammeRepository:
    """Implements ProgrammeRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(programme: Programme) -> dict:
        complexity: dict | None = None
        if programme.complexity_score is not None:
            complexity = {
                "score": programme.complexity_score.score,
                "benchmark_percentile": programme.complexity_score.benchmark_percentile,
            }

        return {
            "id": programme.id,
            "name": programme.name,
            "customer_id": programme.customer_id,
            "sap_source_version": programme.sap_source_version,
            "target_version": programme.target_version,
            "go_live_date": programme.go_live_date.isoformat() if programme.go_live_date else None,
            "status": programme.status.value,
            "complexity_score": complexity,
            "created_at": programme.created_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict) -> Programme:
        complexity: ComplexityScore | None = None
        if data.get("complexity_score") is not None:
            complexity = ComplexityScore(
                score=data["complexity_score"]["score"],
                benchmark_percentile=data["complexity_score"].get("benchmark_percentile"),
            )

        go_live: datetime | None = None
        if data.get("go_live_date") is not None:
            go_live = datetime.fromisoformat(data["go_live_date"])

        return Programme(
            id=data["id"],
            name=data["name"],
            customer_id=data["customer_id"],
            sap_source_version=data["sap_source_version"],
            target_version=data["target_version"],
            go_live_date=go_live,
            status=ProgrammeStatus(data["status"]),
            complexity_score=complexity,
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, programme: Programme) -> None:
        self._store[programme.id] = self._to_dict(programme)

    async def get_by_id(self, id: str) -> Programme | None:
        data = self._store.get(id)
        if data is None:
            return None
        return self._from_dict(data)

    async def list_by_customer(self, customer_id: str) -> list[Programme]:
        return [self._from_dict(data) for data in self._store.values() if data["customer_id"] == customer_id]

    async def list_all(self) -> list[Programme]:
        return [self._from_dict(data) for data in self._store.values()]
