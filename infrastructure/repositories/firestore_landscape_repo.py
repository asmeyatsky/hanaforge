"""Firestore-backed LandscapeRepository — production implementation."""

from __future__ import annotations

from datetime import datetime

from domain.entities.sap_landscape import SAPLandscape
from domain.value_objects.object_type import SystemRole
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "landscapes"


class FirestoreLandscapeRepository(FirestoreBase):
    """Implements LandscapeRepositoryPort using Firestore."""

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

    async def save(self, landscape: SAPLandscape) -> None:
        await self._doc(COLLECTION, landscape.id).set(self._to_dict(landscape))

    async def get_by_id(self, id: str) -> SAPLandscape | None:
        doc = await self._doc(COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_dict(doc.to_dict())

    async def list_by_programme(self, programme_id: str) -> list[SAPLandscape]:
        query = self._collection(COLLECTION).where("programme_id", "==", programme_id)
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]
