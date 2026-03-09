"""Firestore-backed AuditRepository — production implementation for M06."""

from __future__ import annotations

from datetime import datetime

from domain.entities.audit_entry import AuditEntry
from domain.value_objects.migration_types import AuditAction, AuditSeverity
from infrastructure.repositories.firestore_base import FirestoreBase

COLLECTION = "audit_entries"


class FirestoreAuditRepository(FirestoreBase):
    """Implements AuditRepositoryPort using Firestore."""

    @staticmethod
    def _to_dict(entry: AuditEntry) -> dict:
        return {
            "id": entry.id,
            "programme_id": entry.programme_id,
            "timestamp": entry.timestamp.isoformat(),
            "actor": entry.actor,
            "action": entry.action.value,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "details": entry.details,
            "metadata": list(entry.metadata),
            "severity": entry.severity.value,
        }

    @staticmethod
    def _from_dict(data: dict) -> AuditEntry:
        return AuditEntry(
            id=data["id"],
            programme_id=data["programme_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor=data["actor"],
            action=AuditAction(data["action"]),
            resource_type=data["resource_type"],
            resource_id=data["resource_id"],
            details=data["details"],
            metadata=tuple(tuple(pair) for pair in data["metadata"]),
            severity=AuditSeverity(data["severity"]),
        )

    async def save(self, entry: AuditEntry) -> None:
        await self._doc(COLLECTION, entry.id).set(self._to_dict(entry))

    async def list_by_programme(self, programme_id: str, limit: int = 100) -> list[AuditEntry]:
        query = (
            self._collection(COLLECTION)
            .where("programme_id", "==", programme_id)
            .order_by("timestamp", direction="DESCENDING")
            .limit(limit)
        )
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]

    async def list_by_resource(self, resource_type: str, resource_id: str) -> list[AuditEntry]:
        query = (
            self._collection(COLLECTION)
            .where("resource_type", "==", resource_type)
            .where("resource_id", "==", resource_id)
        )
        return [self._from_dict(doc.to_dict()) async for doc in query.stream()]
