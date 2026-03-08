"""GenerateLessonsLearnedUseCase — analyses cutover and hypercare to produce knowledge entries."""

from __future__ import annotations

from domain.events.cutover_events import LessonsLearnedGeneratedEvent
from domain.ports.cutover_ports import (
    CutoverExecutionRepositoryPort,
    HypercareRepositoryPort,
)
from domain.ports.event_bus_ports import EventBusPort
from domain.services.lessons_learned_service import LessonsLearnedService

from application.dtos.cutover_dto import LessonsLearnedResponse


class GenerateLessonsLearnedUseCase:
    """Single-responsibility use case: generate lessons-learned from cutover data."""

    def __init__(
        self,
        execution_repository: CutoverExecutionRepositoryPort,
        hypercare_repository: HypercareRepositoryPort,
        event_bus: EventBusPort,
        lessons_service: LessonsLearnedService | None = None,
    ) -> None:
        self._execution_repo = execution_repository
        self._hypercare_repo = hypercare_repository
        self._event_bus = event_bus
        self._lessons_service = lessons_service or LessonsLearnedService()

    async def execute(self, programme_id: str) -> LessonsLearnedResponse:
        execution = await self._execution_repo.get_active(programme_id)
        if execution is None:
            raise ValueError(f"No active execution found for programme {programme_id}")

        hypercare = await self._hypercare_repo.get_active(programme_id)
        incidents = list(hypercare.incidents) if hypercare else []

        entries = self._lessons_service.generate_lessons_learned(
            execution=execution,
            incidents=incidents,
        )

        # Store entries in hypercare session if available
        if hypercare:
            updated_session = hypercare
            for entry in entries:
                updated_session = updated_session.capture_knowledge(entry)
            await self._hypercare_repo.save(updated_session)

        event = LessonsLearnedGeneratedEvent(
            aggregate_id=programme_id,
            programme_id=programme_id,
            entry_count=len(entries),
        )
        await self._event_bus.publish([event])

        return LessonsLearnedResponse(
            programme_id=programme_id,
            entries=[
                {
                    "id": e.id,
                    "title": e.title,
                    "category": e.category,
                    "content": e.content,
                    "source_task_id": e.source_task_id,
                    "created_at": e.created_at.isoformat(),
                    "created_by": e.created_by,
                }
                for e in entries
            ],
            total=len(entries),
        )
