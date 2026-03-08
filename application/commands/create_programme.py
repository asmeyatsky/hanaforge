"""CreateProgrammeUseCase — creates a new migration programme."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.entities.programme import Programme
from domain.events.programme_events import ProgrammeCreatedEvent
from domain.ports import EventBusPort, ProgrammeRepositoryPort
from domain.value_objects.object_type import ProgrammeStatus

from application.dtos.programme_dto import CreateProgrammeRequest, ProgrammeResponse


class CreateProgrammeUseCase:
    """Single-responsibility use case: create a Programme aggregate and persist it."""

    def __init__(
        self,
        repository: ProgrammeRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus

    async def execute(self, request: CreateProgrammeRequest) -> ProgrammeResponse:
        go_live: datetime | None = None
        if request.go_live_date is not None:
            go_live = datetime.fromisoformat(request.go_live_date)

        now = datetime.now(timezone.utc)
        programme_id = str(uuid.uuid4())

        programme = Programme(
            id=programme_id,
            name=request.name,
            customer_id=request.customer_id,
            sap_source_version=request.sap_source_version,
            target_version=request.target_version,
            go_live_date=go_live,
            status=ProgrammeStatus.CREATED,
            complexity_score=None,
            created_at=now,
        )

        await self._repository.save(programme)

        event = ProgrammeCreatedEvent(
            aggregate_id=programme_id,
            programme_name=request.name,
            customer_id=request.customer_id,
        )
        await self._event_bus.publish(event)

        return ProgrammeResponse.from_entity(programme)
