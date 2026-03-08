"""GetHypercareStatusQuery — retrieves hypercare session status for a programme."""

from __future__ import annotations

from domain.ports.cutover_ports import HypercareRepositoryPort

from application.dtos.cutover_dto import HypercareResponse


class GetHypercareStatusQuery:
    """Read-only query: fetch active hypercare session for a programme."""

    def __init__(
        self,
        hypercare_repository: HypercareRepositoryPort,
    ) -> None:
        self._repository = hypercare_repository

    async def execute(self, programme_id: str) -> HypercareResponse | None:
        session = await self._repository.get_active(programme_id)
        if session is None:
            return None
        return HypercareResponse.from_entity(session)
