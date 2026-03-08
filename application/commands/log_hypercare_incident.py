"""LogHypercareIncidentUseCase — records an incident during the hypercare period."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.events.cutover_events import HypercareIncidentEvent
from domain.ports.cutover_ports import HypercareRepositoryPort, TicketingPort
from domain.ports.event_bus_ports import EventBusPort
from domain.value_objects.cutover_types import HypercareIncident

from application.dtos.cutover_dto import HypercareResponse


class LogHypercareIncidentUseCase:
    """Single-responsibility use case: log an incident and optionally create a ticket."""

    def __init__(
        self,
        hypercare_repository: HypercareRepositoryPort,
        event_bus: EventBusPort,
        ticketing: TicketingPort | None = None,
    ) -> None:
        self._repository = hypercare_repository
        self._event_bus = event_bus
        self._ticketing = ticketing

    async def execute(
        self,
        session_id: str,
        severity: str,
        description: str,
        sap_component: str | None = None,
        ticket_id: str | None = None,
    ) -> HypercareResponse:
        session = await self._repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"Hypercare session {session_id} not found")

        now = datetime.now(timezone.utc)

        # Auto-create a ticket for CRITICAL/HIGH incidents if ticketing adapter available
        if ticket_id is None and self._ticketing and severity in ("CRITICAL", "HIGH"):
            ticket_id = await self._ticketing.create_ticket(
                title=f"[{severity}] {description[:80]}",
                description=description,
                severity=severity,
                component=sap_component or "GENERAL",
            )

        incident = HypercareIncident(
            id=str(uuid.uuid4()),
            severity=severity,
            description=description,
            sap_component=sap_component,
            reported_at=now,
            ticket_id=ticket_id,
        )

        updated = session.log_incident(incident)
        await self._repository.save(updated)

        event = HypercareIncidentEvent(
            aggregate_id=session_id,
            programme_id=session.programme_id,
            severity=severity,
            description=description,
        )
        await self._event_bus.publish([event])

        return HypercareResponse.from_entity(updated)
