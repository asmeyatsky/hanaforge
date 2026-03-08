"""TestForge domain events — emitted during test generation and export lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from domain.events.event_base import DomainEvent


@dataclass(frozen=True)
class TestGenerationStartedEvent(DomainEvent):
    process_area: str = ""
    requested_count: int = 0


@dataclass(frozen=True)
class TestGenerationCompletedEvent(DomainEvent):
    scenarios_generated: int = 0
    process_areas: tuple[str, ...] = ()


@dataclass(frozen=True)
class TestSuiteCreatedEvent(DomainEvent):
    suite_name: str = ""
    scenario_count: int = 0


@dataclass(frozen=True)
class TestExportedEvent(DomainEvent):
    format: str = ""
    scenario_count: int = 0
