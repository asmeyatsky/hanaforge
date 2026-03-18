"""Benchmark value objects — immutable data carriers for migration benchmarking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkCriteria:
    """Filter criteria for finding similar past migrations."""

    source_version: str | None = None
    target_version: str | None = None
    db_size_range: tuple[float, float] | None = None
    object_count_range: tuple[int, int] | None = None
    industry: str | None = None

    def __post_init__(self) -> None:
        if self.db_size_range is not None:
            lo, hi = self.db_size_range
            if lo < 0 or hi < 0:
                raise ValueError("db_size_range values must be non-negative")
            if lo > hi:
                raise ValueError(f"db_size_range lower bound ({lo}) must not exceed upper bound ({hi})")
        if self.object_count_range is not None:
            lo, hi = self.object_count_range
            if lo < 0 or hi < 0:
                raise ValueError("object_count_range values must be non-negative")
            if lo > hi:
                raise ValueError(f"object_count_range lower bound ({lo}) must not exceed upper bound ({hi})")


@dataclass(frozen=True)
class BenchmarkStatistics:
    """Aggregate statistics computed from a set of benchmark entries."""

    total_count: int
    avg_duration_days: float
    median_duration_days: float
    avg_team_size: float
    success_rate: float
    p25_duration: float
    p75_duration: float

    def __post_init__(self) -> None:
        if self.total_count < 0:
            raise ValueError(f"total_count must be non-negative, got {self.total_count}")
        if not (0.0 <= self.success_rate <= 1.0):
            raise ValueError(f"success_rate must be between 0.0 and 1.0, got {self.success_rate}")


@dataclass(frozen=True)
class EstimationResult:
    """Duration estimate with confidence intervals derived from benchmarks."""

    estimated_duration_days: float
    confidence_level: float
    lower_bound_days: float
    upper_bound_days: float
    sample_size: int
    comparable_projects: int
    risk_factors: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.estimated_duration_days < 0:
            raise ValueError("estimated_duration_days must be non-negative")
        if not (0.0 <= self.confidence_level <= 1.0):
            raise ValueError(f"confidence_level must be between 0.0 and 1.0, got {self.confidence_level}")
        if self.lower_bound_days > self.estimated_duration_days:
            raise ValueError("lower_bound_days must not exceed estimated_duration_days")
        if self.upper_bound_days < self.estimated_duration_days:
            raise ValueError("upper_bound_days must not be less than estimated_duration_days")
