"""InMemoryAuditRepository — dev-mode in-memory implementation of AuditRepositoryPort."""

from __future__ import annotations

from datetime import datetime

from domain.entities.audit_entry import AuditEntry
from domain.value_objects.migration_types import AuditAction, AuditSeverity


class InMemoryAuditRepository:
    """Implements AuditRepositoryPort using a plain Python dict."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, entry: AuditEntry) -> None:
        self._store[entry.id] = self._to_dict(entry)

    async def list_by_programme(self, programme_id: str, limit: int = 100) -> list[AuditEntry]:
        entries = [self._from_dict(data) for data in self._store.values() if data["programme_id"] == programme_id]
        # Sort newest first
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    async def list_by_resource(self, resource_type: str, resource_id: str) -> list[AuditEntry]:
        return [
            self._from_dict(data)
            for data in self._store.values()
            if data["resource_type"] == resource_type and data["resource_id"] == resource_id
        ]
