"""GetInfrastructurePlanQuery — retrieves the current infrastructure plan for a programme."""

from __future__ import annotations

from domain.ports.infrastructure_ports import InfrastructurePlanRepositoryPort

from application.dtos.infrastructure_dto import InfrastructurePlanResponse


class GetInfrastructurePlanQuery:
    """Read-only query: fetch the latest infrastructure plan for a programme."""

    def __init__(self, repository: InfrastructurePlanRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, programme_id: str) -> InfrastructurePlanResponse | None:
        plan = await self._repository.get_latest_by_programme(programme_id)
        if plan is None:
            return None
        return InfrastructurePlanResponse.from_entity(plan)
