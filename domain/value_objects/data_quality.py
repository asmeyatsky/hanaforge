"""Data quality value objects — quantify data migration readiness metrics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DataMigrationStatus(Enum):
    NOT_PROFILED = "NOT_PROFILED"
    PROFILING = "PROFILING"
    PROFILED = "PROFILED"
    CLEANSING = "CLEANSING"
    CLEANSED = "CLEANSED"
    TRANSFORMATION_READY = "TRANSFORMATION_READY"
    MIGRATED = "MIGRATED"


class TransformationRuleType(Enum):
    DIRECT_MAP = "DIRECT_MAP"
    VALUE_MAP = "VALUE_MAP"
    CONCATENATE = "CONCATENATE"
    SPLIT = "SPLIT"
    LOOKUP = "LOOKUP"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class FieldNullRate:
    """Captures null statistics for a single field in a dataset."""

    field_name: str
    null_count: int
    total_count: int

    def __post_init__(self) -> None:
        if self.null_count < 0:
            raise ValueError(f"null_count cannot be negative, got {self.null_count}")
        if self.total_count < 0:
            raise ValueError(f"total_count cannot be negative, got {self.total_count}")
        if self.null_count > self.total_count:
            raise ValueError(
                f"null_count ({self.null_count}) cannot exceed total_count ({self.total_count})"
            )

    @property
    def null_percentage(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.null_count / self.total_count) * 100.0


@dataclass(frozen=True)
class DataQualityScore:
    """Composite data quality assessment with weighted scoring."""

    completeness: float
    consistency: float
    accuracy: float

    def __post_init__(self) -> None:
        for name, value in [
            ("completeness", self.completeness),
            ("consistency", self.consistency),
            ("accuracy", self.accuracy),
        ]:
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between 0 and 1, got {value}")

    @property
    def overall(self) -> float:
        """Weighted average: completeness 40%, consistency 35%, accuracy 25%."""
        return self.completeness * 0.40 + self.consistency * 0.35 + self.accuracy * 0.25

    @property
    def risk_level(self) -> str:
        score = self.overall
        if score >= 0.85:
            return "LOW"
        if score >= 0.65:
            return "MEDIUM"
        if score >= 0.40:
            return "HIGH"
        return "CRITICAL"


@dataclass(frozen=True)
class TransformationRule:
    """A single data transformation rule in LTMC-compatible format."""

    source_field: str
    target_field: str
    rule_type: TransformationRuleType
    rule_expression: str
    description: str


@dataclass(frozen=True)
class BPConsolidationResult:
    """Result of Business Partner consolidation readiness assessment."""

    customer_count: int
    vendor_count: int
    duplicate_pairs: int
    merge_candidates: tuple[tuple[str, str], ...]
    consolidation_complexity: str

    def __post_init__(self) -> None:
        if self.consolidation_complexity not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError(
                f"consolidation_complexity must be LOW, MEDIUM, or HIGH, "
                f"got {self.consolidation_complexity}"
            )


@dataclass(frozen=True)
class UniversalJournalAssessment:
    """Assessment of Universal Journal (ACDOCA) migration readiness."""

    custom_coding_blocks: tuple[str, ...]
    profit_centre_assignments: int
    segment_reporting_configs: int
    fi_gl_simplification_impact: str
    migration_complexity: str

    def __post_init__(self) -> None:
        if self.migration_complexity not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError(
                f"migration_complexity must be LOW, MEDIUM, or HIGH, "
                f"got {self.migration_complexity}"
            )
