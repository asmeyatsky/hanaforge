"""Custom ABAP object entity — tracks individual objects through analysis and remediation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.events.analysis_events import ObjectAnalysedEvent
from domain.events.event_base import DomainEvent
from domain.value_objects.effort_points import EffortPoints
from domain.value_objects.object_type import (
    ABAPObjectType,
    BusinessDomain,
    CompatibilityStatus,
    RemediationStatus,
)


@dataclass(frozen=True)
class CustomObject:
    id: str
    landscape_id: str
    object_type: ABAPObjectType
    object_name: str
    package_name: str
    domain: BusinessDomain
    complexity_score: EffortPoints | None
    compatibility_status: CompatibilityStatus
    remediation_status: RemediationStatus
    source_code: str
    deprecated_apis: tuple[str, ...]
    domain_events: tuple[DomainEvent, ...] = ()

    def mark_as_incompatible(self, deprecated_apis: tuple[str, ...]) -> CustomObject:
        event = ObjectAnalysedEvent(
            aggregate_id=self.id,
            object_name=self.object_name,
            compatibility_status=CompatibilityStatus.INCOMPATIBLE.value,
        )
        return replace(
            self,
            compatibility_status=CompatibilityStatus.INCOMPATIBLE,
            deprecated_apis=deprecated_apis,
            domain_events=(*self.domain_events, event),
        )

    def start_remediation(self) -> CustomObject:
        if self.compatibility_status != CompatibilityStatus.INCOMPATIBLE:
            raise ValueError(f"Cannot start remediation for object with status {self.compatibility_status.value}")
        return replace(self, remediation_status=RemediationStatus.IN_PROGRESS)

    def complete_remediation(self) -> CustomObject:
        if self.remediation_status != RemediationStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete remediation from status {self.remediation_status.value}")
        return replace(self, remediation_status=RemediationStatus.REMEDIATED)

    def score_complexity(self, points: EffortPoints) -> CustomObject:
        return replace(self, complexity_score=points)
