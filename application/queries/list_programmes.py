"""ListProgrammesQuery — retrieves programmes, optionally filtered by customer."""

from __future__ import annotations

from domain.ports import ProgrammeRepositoryPort

from application.dtos.programme_dto import (
    ProgrammeListResponse,
    ProgrammeResponse,
)


class ListProgrammesQuery:
    """Read-only query: list programmes with optional customer filter."""

    def __init__(self, repository: ProgrammeRepositoryPort) -> None:
        self._repository = repository

    async def execute(
        self,
        customer_id: str | None = None,
    ) -> ProgrammeListResponse:
        if customer_id is not None:
            programmes = await self._repository.list_by_customer(customer_id)
        else:
            programmes = await self._repository.list_all()

        items = [ProgrammeResponse.from_entity(p) for p in programmes]
        return ProgrammeListResponse(programmes=items, total=len(items))
