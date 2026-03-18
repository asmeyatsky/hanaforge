"""InMemoryLandscapeRepository — dev-mode in-memory implementation of LandscapeRepositoryPort."""

from __future__ import annotations

from datetime import datetime

from domain.entities.sap_landscape import SAPLandscape
from domain.value_objects.object_type import SystemRole


class InMemoryLandscapeRepository:
    """Implements LandscapeRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(landscape: SAPLandscape) -> dict:
        return {
            "id": landscape.id,
            "programme_id": landscape.programme_id,
            "system_id": landscape.system_id,
            "system_role": landscape.system_role.value,
            "db_size_gb": landscape.db_size_gb,
            "number_of_users": landscape.number_of_users,
            "custom_object_count": landscape.custom_object_count,
            "integration_points": list(landscape.integration_points),
            "created_at": landscape.created_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict) -> SAPLandscape:
        return SAPLandscape(
            id=data["id"],
            programme_id=data["programme_id"],
            system_id=data["system_id"],
            system_role=SystemRole(data["system_role"]),
            db_size_gb=data["db_size_gb"],
            number_of_users=data["number_of_users"],
            custom_object_count=data["custom_object_count"],
            integration_points=tuple(data["integration_points"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, landscape: SAPLandscape) -> None:
        self._store[landscape.id] = self._to_dict(landscape)

    async def get_by_id(self, id: str) -> SAPLandscape | None:
        data = self._store.get(id)
        if data is None:
            return None
        return self._from_dict(data)

    async def list_by_programme(self, programme_id: str) -> list[SAPLandscape]:
        return [self._from_dict(data) for data in self._store.values() if data["programme_id"] == programme_id]
