"""TestSuite entity — frozen dataclass grouping test scenarios by process area."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.value_objects.test_types import ProcessArea


@dataclass(frozen=True)
class TestSuite:
    id: str
    programme_id: str
    name: str
    description: str
    process_area: ProcessArea
    scenarios: tuple[str, ...]  # scenario IDs
    coverage_percentage: float
    created_at: datetime

    def add_scenario(self, scenario_id: str) -> TestSuite:
        """Return a new TestSuite with the given scenario ID appended."""
        if scenario_id in self.scenarios:
            return self
        return replace(self, scenarios=(*self.scenarios, scenario_id))

    def calculate_coverage(self, total_processes: int) -> TestSuite:
        """Return a new TestSuite with coverage_percentage recalculated."""
        if total_processes <= 0:
            return replace(self, coverage_percentage=0.0)
        pct = min(100.0, (len(self.scenarios) / total_processes) * 100.0)
        return replace(self, coverage_percentage=round(pct, 2))
