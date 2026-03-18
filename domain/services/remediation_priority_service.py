"""Remediation priority — sorts the backlog by business impact and effort."""

from __future__ import annotations

from typing import TYPE_CHECKING

from domain.entities.custom_object import CustomObject
from domain.value_objects.object_type import BusinessDomain, CompatibilityStatus

if TYPE_CHECKING:
    from domain.entities.remediation import RemediationSuggestion

_DOMAIN_CRITICALITY: dict[BusinessDomain, int] = {
    BusinessDomain.FI: 0,
    BusinessDomain.SD: 1,
    BusinessDomain.MM: 2,
    BusinessDomain.CO: 3,
    BusinessDomain.PP: 4,
    BusinessDomain.HCM: 5,
    BusinessDomain.QM: 6,
    BusinessDomain.PM: 7,
    BusinessDomain.PS: 8,
    BusinessDomain.WM: 9,
    BusinessDomain.EWMS: 10,
    BusinessDomain.BASIS: 11,
    BusinessDomain.CROSS_APPLICATION: 12,
    BusinessDomain.UNKNOWN: 13,
}


class RemediationPriorityService:
    def prioritize_backlog(self, objects: list[CustomObject]) -> list[CustomObject]:
        return sorted(objects, key=self._sort_key)

    async def prioritize(self, suggestions: list[RemediationSuggestion]) -> list[RemediationSuggestion]:
        """Sort remediation suggestions by confidence score (highest first)."""
        return sorted(suggestions, key=lambda s: s.confidence_score, reverse=True)

    @staticmethod
    def _sort_key(obj: CustomObject) -> tuple[int, int, int]:
        incompatible_order = 0 if obj.compatibility_status == CompatibilityStatus.INCOMPATIBLE else 1

        effort_order = -(obj.complexity_score.points if obj.complexity_score else 0)

        domain_order = _DOMAIN_CRITICALITY.get(obj.domain, 99)

        return (incompatible_order, effort_order, domain_order)
