"""Migration approach value objects — encapsulates strategic migration options."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MigrationApproach(Enum):
    GREENFIELD = "GREENFIELD"
    BROWNFIELD = "BROWNFIELD"
    SELECTIVE_DATA_TRANSITION = "SELECTIVE_DATA_TRANSITION"
    RISE_WITH_SAP = "RISE_WITH_SAP"


@dataclass(frozen=True)
class MigrationRecommendation:
    approach: MigrationApproach
    confidence: float
    reasoning: str

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0 and 1, got {self.confidence}")
