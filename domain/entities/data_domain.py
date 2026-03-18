"""DataDomain entity — represents a single SAP table dataset under migration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from domain.events.event_base import DomainEvent
from domain.value_objects.data_quality import (
    DataMigrationStatus,
    DataQualityScore,
    FieldNullRate,
    TransformationRule,
)


@dataclass(frozen=True)
class DataDomain:
    id: str
    landscape_id: str
    table_name: str
    record_count: int
    field_count: int
    null_rates: tuple[FieldNullRate, ...]
    duplicate_key_count: int
    referential_integrity_score: float
    encoding_issues: tuple[str, ...]
    migration_status: DataMigrationStatus
    transformation_rules: tuple[TransformationRule, ...]
    quality_score: DataQualityScore | None
    created_at: datetime
    domain_events: tuple[DomainEvent, ...] = ()

    def profile_complete(
        self,
        null_rates: tuple[FieldNullRate, ...],
        dup_count: int,
        ref_score: float,
        encoding_issues: tuple[str, ...],
    ) -> DataDomain:
        """Return a new DataDomain with profiling results applied."""
        if not (0.0 <= ref_score <= 1.0):
            raise ValueError(f"referential_integrity_score must be between 0 and 1, got {ref_score}")
        return replace(
            self,
            null_rates=null_rates,
            duplicate_key_count=dup_count,
            referential_integrity_score=ref_score,
            encoding_issues=encoding_issues,
            migration_status=DataMigrationStatus.PROFILED,
        )

    def add_transformation_rule(self, rule: TransformationRule) -> DataDomain:
        """Return a new DataDomain with an additional transformation rule."""
        return replace(
            self,
            transformation_rules=(*self.transformation_rules, rule),
        )

    def mark_migration_ready(self) -> DataDomain:
        """Transition the entity to TRANSFORMATION_READY status."""
        if self.migration_status not in (
            DataMigrationStatus.PROFILED,
            DataMigrationStatus.CLEANSED,
        ):
            raise ValueError(
                f"Cannot mark migration ready from status {self.migration_status.value}; must be PROFILED or CLEANSED"
            )
        return replace(
            self,
            migration_status=DataMigrationStatus.TRANSFORMATION_READY,
        )
