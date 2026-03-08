"""Data readiness domain events — emitted during data profiling and assessment."""

from __future__ import annotations

from dataclasses import dataclass

from domain.events.event_base import DomainEvent


@dataclass(frozen=True)
class DataProfilingStartedEvent(DomainEvent):
    landscape_id: str = ""
    table_count: int = 0


@dataclass(frozen=True)
class DataProfilingCompletedEvent(DomainEvent):
    landscape_id: str = ""
    tables_profiled: int = 0
    overall_quality: float = 0.0


@dataclass(frozen=True)
class BPConsolidationAssessedEvent(DomainEvent):
    landscape_id: str = ""
    merge_candidates: int = 0


@dataclass(frozen=True)
class TransformationRulesGeneratedEvent(DomainEvent):
    landscape_id: str = ""
    rule_count: int = 0
