"""Programme aggregate root — orchestrates the full migration lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.events.event_base import DomainEvent
from domain.events.programme_events import (
    AnalysisCompletedEvent,
    AnalysisStartedEvent,
    DiscoveryCompletedEvent,
    DiscoveryStartedEvent,
)
from domain.value_objects.complexity_score import ComplexityScore
from domain.value_objects.object_type import ProgrammeStatus

_VALID_TRANSITIONS: dict[ProgrammeStatus, tuple[ProgrammeStatus, ...]] = {
    ProgrammeStatus.CREATED: (ProgrammeStatus.DISCOVERY_IN_PROGRESS,),
    ProgrammeStatus.DISCOVERY_IN_PROGRESS: (ProgrammeStatus.DISCOVERY_COMPLETE,),
    ProgrammeStatus.DISCOVERY_COMPLETE: (ProgrammeStatus.ANALYSIS_IN_PROGRESS,),
    ProgrammeStatus.ANALYSIS_IN_PROGRESS: (ProgrammeStatus.ANALYSIS_COMPLETE,),
    ProgrammeStatus.ANALYSIS_COMPLETE: (ProgrammeStatus.REMEDIATION_IN_PROGRESS,),
    ProgrammeStatus.REMEDIATION_IN_PROGRESS: (ProgrammeStatus.MIGRATION_READY,),
    ProgrammeStatus.MIGRATION_READY: (ProgrammeStatus.MIGRATION_IN_PROGRESS,),
    ProgrammeStatus.MIGRATION_IN_PROGRESS: (ProgrammeStatus.CUTOVER,),
    ProgrammeStatus.CUTOVER: (ProgrammeStatus.HYPERCARE,),
    ProgrammeStatus.HYPERCARE: (ProgrammeStatus.COMPLETED,),
    ProgrammeStatus.COMPLETED: (),
}


@dataclass(frozen=True)
class Programme:
    id: str
    name: str
    customer_id: str
    sap_source_version: str
    target_version: str
    go_live_date: datetime | None
    status: ProgrammeStatus
    complexity_score: ComplexityScore | None
    created_at: datetime
    domain_events: tuple[DomainEvent, ...] = ()

    def update_status(self, new_status: ProgrammeStatus) -> Programme:
        allowed = _VALID_TRANSITIONS.get(self.status, ())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid status transition from {self.status.value} to {new_status.value}"
            )
        return replace(self, status=new_status)

    def start_discovery(self) -> Programme:
        updated = self.update_status(ProgrammeStatus.DISCOVERY_IN_PROGRESS)
        event = DiscoveryStartedEvent(aggregate_id=self.id, landscape_id="")
        return replace(updated, domain_events=(*updated.domain_events, event))

    def complete_discovery(self, score: ComplexityScore) -> Programme:
        updated = self.update_status(ProgrammeStatus.DISCOVERY_COMPLETE)
        event = DiscoveryCompletedEvent(
            aggregate_id=self.id, complexity_score=score.score
        )
        return replace(
            updated,
            complexity_score=score,
            domain_events=(*updated.domain_events, event),
        )

    def start_analysis(self) -> Programme:
        updated = self.update_status(ProgrammeStatus.ANALYSIS_IN_PROGRESS)
        event = AnalysisStartedEvent(aggregate_id=self.id, object_count=0)
        return replace(updated, domain_events=(*updated.domain_events, event))

    def complete_analysis(self) -> Programme:
        updated = self.update_status(ProgrammeStatus.ANALYSIS_COMPLETE)
        event = AnalysisCompletedEvent(
            aggregate_id=self.id, compatible_count=0, incompatible_count=0
        )
        return replace(updated, domain_events=(*updated.domain_events, event))
