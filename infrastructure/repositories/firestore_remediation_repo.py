"""Firestore-backed RemediationRepository — production implementation."""

from __future__ import annotations

from datetime import datetime

from domain.entities.remediation import RemediationSuggestion
from domain.value_objects.object_type import ReviewStatus
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "remediation_suggestions"


class FirestoreRemediationRepository(FirestoreBase):
    """Implements RemediationRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(suggestion: RemediationSuggestion) -> dict:
        return {
            "id": suggestion.id,
            "object_id": suggestion.object_id,
            "issue_type": suggestion.issue_type,
            "deprecated_api": suggestion.deprecated_api,
            "suggested_replacement": suggestion.suggested_replacement,
            "generated_code": suggestion.generated_code,
            "confidence_score": suggestion.confidence_score,
            "reviewed_by": suggestion.reviewed_by,
            "status": suggestion.status.value,
            "created_at": suggestion.created_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict) -> RemediationSuggestion:
        return RemediationSuggestion(
            id=data["id"],
            object_id=data["object_id"],
            issue_type=data["issue_type"],
            deprecated_api=data["deprecated_api"],
            suggested_replacement=data["suggested_replacement"],
            generated_code=data["generated_code"],
            confidence_score=data["confidence_score"],
            reviewed_by=data.get("reviewed_by"),
            status=ReviewStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    async def save(self, suggestion: RemediationSuggestion) -> None:
        await self._doc(COLLECTION, suggestion.id).set(self._to_dict(suggestion))

    async def save_batch(self, suggestions: list[RemediationSuggestion]) -> None:
        batch = self.client.batch()
        for s in suggestions:
            batch.set(self._doc(COLLECTION, s.id), self._to_dict(s))
        await batch.commit()

    async def get_by_object(self, object_id: str) -> list[RemediationSuggestion]:
        query = self._collection(COLLECTION).where("object_id", "==", object_id)
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]

    async def get_by_object_ids(self, object_ids: list[str]) -> list[RemediationSuggestion]:
        # Firestore 'in' queries support up to 30 values; chunk if needed
        results: list[RemediationSuggestion] = []
        for i in range(0, len(object_ids), 30):
            chunk = object_ids[i : i + 30]
            query = self._collection(COLLECTION).where("object_id", "in", chunk)
            async for doc in query.stream():
                results.append(self._from_dict(doc.to_dict()))
        return results

    async def list_by_programme(self, programme_id: str) -> list[RemediationSuggestion]:
        query = self._collection(COLLECTION).where("programme_id", "==", programme_id)
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]
