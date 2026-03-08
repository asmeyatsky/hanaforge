"""StartHypercareUseCase — initiates a hypercare monitoring session post go-live."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from domain.entities.hypercare_session import HypercareSession
from domain.events.cutover_events import HypercareStartedEvent
from domain.ports.cutover_ports import HypercareRepositoryPort
from domain.ports.event_bus_ports import EventBusPort
from domain.value_objects.cutover_types import HypercareStatus, MonitoringConfig

from application.dtos.cutover_dto import HypercareResponse


class StartHypercareUseCase:
    """Single-responsibility use case: create and persist a new HypercareSession."""

    def __init__(
        self,
        hypercare_repository: HypercareRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._repository = hypercare_repository
        self._event_bus = event_bus

    async def execute(
        self,
        programme_id: str,
        duration_days: int = 90,
        monitoring_config: dict | None = None,
    ) -> HypercareResponse:
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=duration_days)

        config = MonitoringConfig(
            alert_channels=tuple(
                monitoring_config.get("alert_channels", ["email", "slack"])
                if monitoring_config
                else ["email", "slack"]
            ),
            check_interval_minutes=(
                monitoring_config.get("check_interval_minutes", 15)
                if monitoring_config
                else 15
            ),
            escalation_contacts=tuple(
                monitoring_config.get("escalation_contacts", [])
                if monitoring_config
                else []
            ),
            sla_response_minutes=(
                monitoring_config.get("sla_response_minutes", 30)
                if monitoring_config
                else 30
            ),
        )

        session_id = str(uuid.uuid4())
        session = HypercareSession(
            id=session_id,
            programme_id=programme_id,
            start_date=now,
            end_date=end_date,
            status=HypercareStatus.ACTIVE,
            monitoring_config=config,
            created_at=now,
        )

        await self._repository.save(session)

        event = HypercareStartedEvent(
            aggregate_id=session_id,
            programme_id=programme_id,
            duration_days=duration_days,
        )
        await self._event_bus.publish([event])

        return HypercareResponse.from_entity(session)
