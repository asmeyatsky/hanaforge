"""GetAuditLogQuery — retrieves the audit log for a migration programme."""

from __future__ import annotations

from domain.ports.migration_ports import AuditRepositoryPort

from application.dtos.migration_dto import AuditEntryResponse, AuditLogResponse


class GetAuditLogQuery:
    """Read-only query: returns the audit log entries for a programme."""

    def __init__(self, audit_repo: AuditRepositoryPort) -> None:
        self._audit_repo = audit_repo

    async def execute(
        self, programme_id: str, limit: int = 100
    ) -> AuditLogResponse:
        """Retrieve audit log entries, newest first."""
        entries = await self._audit_repo.list_by_programme(programme_id, limit=limit)

        return AuditLogResponse(
            programme_id=programme_id,
            entries=[AuditEntryResponse.from_entity(e) for e in entries],
            total=len(entries),
        )
