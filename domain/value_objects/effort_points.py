"""Effort points value object — T-shirt sized complexity for individual objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EffortPoints:
    points: int
    description: str

    def __post_init__(self) -> None:
        if not (1 <= self.points <= 5):
            raise ValueError(f"points must be between 1 and 5, got {self.points}")

    @classmethod
    def trivial(cls) -> EffortPoints:
        return cls(points=1, description="Trivial — automated fix or no change needed")

    @classmethod
    def low(cls) -> EffortPoints:
        return cls(points=2, description="Low — minor code adjustment required")

    @classmethod
    def medium(cls) -> EffortPoints:
        return cls(points=3, description="Medium — moderate refactoring needed")

    @classmethod
    def high(cls) -> EffortPoints:
        return cls(points=4, description="High — significant rework required")

    @classmethod
    def critical(cls) -> EffortPoints:
        return cls(points=5, description="Critical — complete rewrite or architectural change")
