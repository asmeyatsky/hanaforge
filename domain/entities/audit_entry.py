"""AuditEntry entity — immutable audit log record for compliance and traceability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.value_objects.migration_types import AuditAction, AuditSeverity


@dataclass(frozen=True)
class AuditEntry:
    """A single audit log entry recording an action in the migration programme.

    Frozen dataclass — once created, an audit entry is immutable.
    metadata is stored as a tuple of (key, value) pairs for immutability.
    """

    id: str
    programme_id: str
    timestamp: datetime
    actor: str
    action: AuditAction
    resource_type: str
    resource_id: str
    details: str
    metadata: tuple[tuple[str, str], ...]
    severity: AuditSeverity
