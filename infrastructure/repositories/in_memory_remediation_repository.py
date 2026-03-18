"""InMemoryRemediationRepository — dev-mode in-memory implementation of RemediationRepositoryPort."""

from __future__ import annotations

from datetime import datetime

from domain.entities.remediation import RemediationSuggestion
from domain.value_objects.object_type import ReviewStatus


class InMemoryRemediationRepository:
    """Implements RemediationRepositoryPort using a plain Python dict.

    To support list_by_programme we maintain an auxiliary index mapping
    object_id -> list[suggestion_id].  The full programme-level query
    requires joining through the custom-object repository, but for the
    in-memory dev variant we store a programme_id hint on each record
    when available.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, suggestion: RemediationSuggestion) -> None:
        self._store[suggestion.id] = self._to_dict(suggestion)

    async def get_by_object(self, object_id: str) -> list[RemediationSuggestion]:
        return [self._from_dict(data) for data in self._store.values() if data["object_id"] == object_id]

    async def get_by_object_ids(self, object_ids: list[str]) -> list[RemediationSuggestion]:
        id_set = set(object_ids)
        return [self._from_dict(data) for data in self._store.values() if data["object_id"] in id_set]

    async def list_by_programme(self, programme_id: str) -> list[RemediationSuggestion]:
        """Return all remediation suggestions across the programme.

        In the in-memory implementation we return every stored suggestion.
        The Firestore-backed version will filter via a programme_id field
        added during persistence by the use case layer.
        """
        return [self._from_dict(data) for data in self._store.values()]
