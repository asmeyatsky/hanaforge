"""Firestore-backed CustomObjectRepository — production implementation."""

from __future__ import annotations

from domain.entities.custom_object import CustomObject
from domain.value_objects.effort_points import EffortPoints
from domain.value_objects.object_type import (
    ABAPObjectType,
    BusinessDomain,
    CompatibilityStatus,
    RemediationStatus,
)
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "custom_objects"


class FirestoreCustomObjectRepository(FirestoreBase):
    """Implements CustomObjectRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(obj: CustomObject) -> dict:
        complexity: dict | None = None
        if obj.complexity_score is not None:
            complexity = {
                "points": obj.complexity_score.points,
                "description": obj.complexity_score.description,
            }
        return {
            "id": obj.id,
            "landscape_id": obj.landscape_id,
            "object_type": obj.object_type.value,
            "object_name": obj.object_name,
            "package_name": obj.package_name,
            "domain": obj.domain.value,
            "complexity_score": complexity,
            "compatibility_status": obj.compatibility_status.value,
            "remediation_status": obj.remediation_status.value,
            "source_code": obj.source_code,
            "deprecated_apis": list(obj.deprecated_apis),
        }

    @staticmethod
    def _from_dict(data: dict) -> CustomObject:
        complexity: EffortPoints | None = None
        if data.get("complexity_score") is not None:
            complexity = EffortPoints(
                points=data["complexity_score"]["points"],
                description=data["complexity_score"]["description"],
            )
        return CustomObject(
            id=data["id"],
            landscape_id=data["landscape_id"],
            object_type=ABAPObjectType(data["object_type"]),
            object_name=data["object_name"],
            package_name=data["package_name"],
            domain=BusinessDomain(data["domain"]),
            complexity_score=complexity,
            compatibility_status=CompatibilityStatus(data["compatibility_status"]),
            remediation_status=RemediationStatus(data["remediation_status"]),
            source_code=data["source_code"],
            deprecated_apis=tuple(data["deprecated_apis"]),
        )

    async def save(self, obj: CustomObject) -> None:
        await self._doc(COLLECTION, obj.id).set(self._to_dict(obj))

    async def save_batch(self, objs: list[CustomObject]) -> None:
        batch = self.client.batch()
        for obj in objs:
            ref = self._doc(COLLECTION, obj.id)
            batch.set(ref, self._to_dict(obj))
        await batch.commit()

    async def get_by_id(self, id: str) -> CustomObject | None:
        doc = await self._doc(COLLECTION, id).get()
        if not doc.exists:
            return None
        return self._from_dict(doc.to_dict())

    async def get_by_landscape(self, landscape_id: str) -> list[CustomObject]:
        query = self._collection(COLLECTION).where("landscape_id", "==", landscape_id)
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]

    async def list_by_landscape(self, landscape_id: str) -> list[CustomObject]:
        return await self.get_by_landscape(landscape_id)

    async def count_by_status(self, landscape_id: str, status: CompatibilityStatus) -> int:
        query = (
            self._collection(COLLECTION)
            .where("landscape_id", "==", landscape_id)
            .where("compatibility_status", "==", status.value)
        )
        count = 0
        async for _ in query.stream():
            count += 1
        return count
