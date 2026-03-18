"""AI analysis ports — boundaries for LLM-powered code analysis and migration advice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.value_objects.migration_approach import MigrationRecommendation
from domain.value_objects.object_type import ABAPObjectType


@dataclass(frozen=True)
class AnalysisResult:
    compatible: bool
    deprecated_apis: list[str]
    issues: list[str]
    remediation_code: str | None
    confidence: float
    # Extended fields for remediation workflow
    compatibility_status: str = "UNKNOWN"
    issue_type: str | None = None
    deprecated_api: str | None = None
    suggested_replacement: str | None = None
    generated_code: str | None = None
    confidence_score: float = 0.5
    effort_points: int | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be between 0 and 1, got {self.confidence}"
            )


class ABAPAnalysisPort(Protocol):
    async def analyze_object(
        self,
        source_code: str,
        object_type: ABAPObjectType,
        sap_source_version: str,
        target_version: str,
    ) -> AnalysisResult: ...


class MigrationAdvisorPort(Protocol):
    async def recommend_approach(
        self, landscape_summary: dict
    ) -> MigrationRecommendation: ...
