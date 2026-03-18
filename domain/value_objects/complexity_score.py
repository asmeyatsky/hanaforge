"""Complexity score value object — quantifies migration risk on a 1-100 scale."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComplexityScore:
    score: int
    benchmark_percentile: float | None = None

    def __post_init__(self) -> None:
        if not (1 <= self.score <= 100):
            raise ValueError(f"score must be between 1 and 100, got {self.score}")
        if self.benchmark_percentile is not None and not (0.0 <= self.benchmark_percentile <= 100.0):
            raise ValueError(f"benchmark_percentile must be between 0 and 100, got {self.benchmark_percentile}")

    @property
    def risk_level(self) -> str:
        if self.score <= 25:
            return "LOW"
        if self.score <= 50:
            return "MEDIUM"
        if self.score <= 75:
            return "HIGH"
        return "CRITICAL"
