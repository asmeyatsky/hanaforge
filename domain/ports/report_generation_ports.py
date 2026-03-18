"""Report generation port — boundary for PDF/document rendering infrastructure."""

from __future__ import annotations

from typing import Any, Protocol

from domain.entities.programme import Programme
from domain.value_objects.complexity_score import ComplexityScore


class ReportGeneratorPort(Protocol):
    async def generate_assessment_report(
        self,
        programme: Programme,
        landscapes: list[Any],
        objects: list[Any],
        remediations: list[Any],
    ) -> bytes: ...

    async def generate_executive_summary(
        self,
        programme: Programme,
        complexity: ComplexityScore,
    ) -> str: ...

    async def generate_board_presentation(
        self,
        programme: Programme,
        landscapes: list[Any],
        objects: list[Any],
        remediations: list[Any],
        complexity: ComplexityScore,
        recommendation: str,
    ) -> bytes: ...
