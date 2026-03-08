"""TestScenario entity — frozen dataclass representing a single test scenario."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.events.event_base import DomainEvent
from domain.value_objects.test_types import (
    ProcessArea,
    TestPriority,
    TestStatus,
    TestStep,
)


@dataclass(frozen=True)
class TestScenario:
    id: str
    programme_id: str
    process_area: ProcessArea
    scenario_name: str
    description: str
    preconditions: tuple[str, ...]
    steps: tuple[TestStep, ...]
    expected_outcome: str
    sap_transaction: str | None
    fiori_app_id: str | None
    priority: TestPriority
    status: TestStatus
    tags: tuple[str, ...]
    created_at: datetime
    domain_events: tuple[DomainEvent, ...] = ()

    def mark_as_reviewed(self) -> TestScenario:
        """Transition scenario to REVIEWED status."""
        if self.status != TestStatus.DRAFT:
            raise ValueError(
                f"Cannot review scenario in status {self.status.value}; must be DRAFT"
            )
        return replace(self, status=TestStatus.REVIEWED)

    def link_to_defect(self, defect_id: str) -> TestScenario:
        """Add a defect ID to the scenario tags for traceability."""
        defect_tag = f"defect:{defect_id}"
        if defect_tag in self.tags:
            return self
        return replace(self, tags=(*self.tags, defect_tag))

    def update_status(self, status: TestStatus) -> TestScenario:
        """Update the scenario status."""
        return replace(self, status=status)
