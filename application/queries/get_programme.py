"""GetProgrammeQuery — retrieves a single programme by ID."""

from __future__ import annotations

from domain.ports import ProgrammeRepositoryPort

from application.dtos.programme_dto import ProgrammeResponse


class GetProgrammeQuery:
    """Read-only query: fetch a programme by its identifier."""

    def __init__(self, repository: ProgrammeRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, programme_id: str) -> ProgrammeResponse | None:
        programme = await self._repository.get_by_id(programme_id)
        if programme is None:
            return None
        return ProgrammeResponse.from_entity(programme)
