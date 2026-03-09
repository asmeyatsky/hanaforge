"""BenchmarkEntry entity — a historical SAP migration data point for estimation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BenchmarkEntry:
    """Immutable record of a completed SAP migration used for benchmarking.

    Each entry captures the key parameters and outcome of a real-world
    SAP S/4HANA migration, enabling statistical estimation for new programmes.
    """

    id: str
    source_version: str
    target_version: str
    db_size_gb: float
    custom_object_count: int
    duration_days: int
    team_size: int
    complexity_score: int
    industry: str
    region: str
    success: bool
    lessons_learned: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if self.db_size_gb < 0:
            raise ValueError(f"db_size_gb must be non-negative, got {self.db_size_gb}")
        if self.custom_object_count < 0:
            raise ValueError(f"custom_object_count must be non-negative, got {self.custom_object_count}")
        if self.duration_days < 0:
            raise ValueError(f"duration_days must be non-negative, got {self.duration_days}")
        if self.team_size < 1:
            raise ValueError(f"team_size must be at least 1, got {self.team_size}")
        if not (1 <= self.complexity_score <= 100):
            raise ValueError(f"complexity_score must be between 1 and 100, got {self.complexity_score}")
