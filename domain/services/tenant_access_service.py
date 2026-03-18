"""Tenant access service — enforces programme ownership for multi-tenancy.

All access checks are pure domain logic: they load the aggregate and verify
that the requesting tenant actually owns it.  This keeps the enforcement
independent of any infrastructure or presentation concern.
"""

from __future__ import annotations

from domain.entities.programme import Programme
from domain.ports.repository_ports import ProgrammeRepositoryPort


class TenantAccessService:
    """Validates that a tenant has access to the requested programme."""

    def __init__(self, programme_repository: ProgrammeRepositoryPort) -> None:
        self._programme_repo = programme_repository

    async def validate_programme_access(
        self,
        programme_id: str,
        customer_id: str,
    ) -> Programme:
        """Load a programme and verify the caller owns it.

        Returns the programme on success.
        Raises ``ValueError`` if the programme does not exist or does not
        belong to the given customer.
        """
        programme = await self._programme_repo.get_by_id(programme_id)
        if programme is None:
            raise ValueError(f"Programme {programme_id!r} not found")
        if programme.customer_id != customer_id:
            # Intentionally vague — do not reveal that the programme exists
            # to a tenant who does not own it.
            raise ValueError(f"Programme {programme_id!r} not found")
        return programme

    @staticmethod
    async def filter_by_tenant(
        programmes: list[Programme],
        customer_id: str,
    ) -> list[Programme]:
        """Return only the programmes that belong to *customer_id*."""
        return [p for p in programmes if p.customer_id == customer_id]
