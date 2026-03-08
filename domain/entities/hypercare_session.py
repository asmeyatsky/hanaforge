"""HypercareSession aggregate — manages the 90-day hypercare window post go-live."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from domain.events.event_base import DomainEvent
from domain.value_objects.cutover_types import (
    HypercareIncident,
    HypercareStatus,
    KnowledgeEntry,
    MonitoringConfig,
)


@dataclass(frozen=True)
class HypercareSession:
    """Immutable aggregate tracking the post-go-live hypercare period."""

    id: str
    programme_id: str
    start_date: datetime
    end_date: datetime
    status: HypercareStatus = HypercareStatus.ACTIVE
    monitoring_config: MonitoringConfig = MonitoringConfig()
    incidents: tuple[HypercareIncident, ...] = ()
    knowledge_entries: tuple[KnowledgeEntry, ...] = ()
    created_at: datetime = None  # type: ignore[assignment]
    domain_events: tuple[DomainEvent, ...] = ()

    def __post_init__(self) -> None:
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc))

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def log_incident(self, incident: HypercareIncident) -> HypercareSession:
        """Record a new incident and escalate if severity is CRITICAL."""
        new_status = self.status
        if incident.severity == "CRITICAL":
            new_status = HypercareStatus.ESCALATED
        return replace(
            self,
            incidents=(*self.incidents, incident),
            status=new_status,
        )

    def capture_knowledge(self, entry: KnowledgeEntry) -> HypercareSession:
        """Add a knowledge/lessons-learned entry to the session."""
        return replace(self, knowledge_entries=(*self.knowledge_entries, entry))

    def close_session(self) -> HypercareSession:
        """Close the hypercare session."""
        if self.status == HypercareStatus.CLOSED:
            raise ValueError("Session is already closed")
        return replace(self, status=HypercareStatus.CLOSED)

    def resolve_incident(
        self, incident_id: str, resolution: str
    ) -> HypercareSession:
        """Mark an incident as resolved."""
        now = datetime.now(timezone.utc)
        updated: list[HypercareIncident] = []
        found = False
        for inc in self.incidents:
            if inc.id == incident_id:
                found = True
                updated.append(
                    HypercareIncident(
                        id=inc.id,
                        severity=inc.severity,
                        description=inc.description,
                        sap_component=inc.sap_component,
                        reported_at=inc.reported_at,
                        resolved_at=now,
                        resolution=resolution,
                        ticket_id=inc.ticket_id,
                    )
                )
            else:
                updated.append(inc)
        if not found:
            raise ValueError(f"Incident {incident_id} not found")

        # De-escalate if no open critical incidents remain
        new_status = self.status
        if self.status == HypercareStatus.ESCALATED:
            open_critical = any(
                i.severity == "CRITICAL" and i.resolved_at is None
                for i in updated
            )
            if not open_critical:
                new_status = HypercareStatus.ACTIVE

        return replace(self, incidents=tuple(updated), status=new_status)
