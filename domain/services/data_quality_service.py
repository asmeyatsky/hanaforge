"""Data quality service — pure domain logic for quality assessment and risk registers."""

from __future__ import annotations

from dataclasses import dataclass

from domain.entities.data_domain import DataDomain
from domain.value_objects.data_quality import DataQualityScore


@dataclass(frozen=True)
class DataRiskEntry:
    """A single entry in the data migration risk register."""

    table_name: str
    risk_level: str
    risk_category: str
    description: str
    recommended_action: str
    priority: int

    def __post_init__(self) -> None:
        if not (1 <= self.priority <= 5):
            raise ValueError(f"priority must be between 1 and 5, got {self.priority}")


class DataQualityService:
    """Assesses dataset quality and generates prioritised risk registers."""

    def assess_dataset_quality(self, data_domain: DataDomain) -> DataQualityScore:
        """Calculate a DataQualityScore from profiling results.

        - completeness: derived from average null rates across fields
        - consistency: derived from referential integrity score
        - accuracy: derived from encoding issue count
        """
        # Completeness: average non-null percentage across all fields
        if data_domain.null_rates:
            avg_null_pct = sum(nr.null_percentage for nr in data_domain.null_rates) / len(data_domain.null_rates)
            completeness = max(0.0, min(1.0, 1.0 - (avg_null_pct / 100.0)))
        else:
            completeness = 1.0

        # Consistency: referential integrity score (already 0-1)
        consistency = max(0.0, min(1.0, data_domain.referential_integrity_score))

        # Accuracy: penalise for encoding issues
        encoding_count = len(data_domain.encoding_issues)
        if encoding_count == 0:
            accuracy = 1.0
        elif encoding_count <= 2:
            accuracy = 0.8
        elif encoding_count <= 5:
            accuracy = 0.6
        elif encoding_count <= 10:
            accuracy = 0.4
        else:
            accuracy = 0.2

        return DataQualityScore(
            completeness=round(completeness, 4),
            consistency=round(consistency, 4),
            accuracy=round(accuracy, 4),
        )

    def generate_risk_register(self, domains: list[DataDomain]) -> list[DataRiskEntry]:
        """Generate a prioritised risk register across all data domains."""
        entries: list[DataRiskEntry] = []

        for domain in domains:
            quality = domain.quality_score
            if quality is None:
                entries.append(
                    DataRiskEntry(
                        table_name=domain.table_name,
                        risk_level="CRITICAL",
                        risk_category="NOT_PROFILED",
                        description=f"Table {domain.table_name} has not been profiled",
                        recommended_action="Run data profiling before migration",
                        priority=1,
                    )
                )
                continue

            # High null rates
            if quality.completeness < 0.5:
                entries.append(
                    DataRiskEntry(
                        table_name=domain.table_name,
                        risk_level="HIGH",
                        risk_category="DATA_COMPLETENESS",
                        description=(f"Table {domain.table_name} has low completeness ({quality.completeness:.0%})"),
                        recommended_action=(
                            "Investigate null fields and apply default value rules "
                            "or flag mandatory fields for cleansing"
                        ),
                        priority=2,
                    )
                )

            # Duplicate keys
            if domain.duplicate_key_count > 0:
                severity = "CRITICAL" if domain.duplicate_key_count > 100 else "HIGH"
                prio = 1 if severity == "CRITICAL" else 2
                entries.append(
                    DataRiskEntry(
                        table_name=domain.table_name,
                        risk_level=severity,
                        risk_category="DUPLICATE_KEYS",
                        description=(
                            f"Table {domain.table_name} has {domain.duplicate_key_count} duplicate key records"
                        ),
                        recommended_action=("De-duplicate records or define merge strategy before migration"),
                        priority=prio,
                    )
                )

            # Low referential integrity
            if quality.consistency < 0.7:
                entries.append(
                    DataRiskEntry(
                        table_name=domain.table_name,
                        risk_level="HIGH",
                        risk_category="REFERENTIAL_INTEGRITY",
                        description=(
                            f"Table {domain.table_name} has low referential integrity ({quality.consistency:.0%})"
                        ),
                        recommended_action=("Validate foreign key references and repair orphaned records"),
                        priority=2,
                    )
                )

            # Encoding issues
            if domain.encoding_issues:
                entries.append(
                    DataRiskEntry(
                        table_name=domain.table_name,
                        risk_level="MEDIUM",
                        risk_category="ENCODING",
                        description=(f"Table {domain.table_name} has {len(domain.encoding_issues)} encoding issues"),
                        recommended_action=("Convert affected fields to UTF-8 encoding before load"),
                        priority=3,
                    )
                )

            # Overall low quality
            if quality.overall < 0.4:
                entries.append(
                    DataRiskEntry(
                        table_name=domain.table_name,
                        risk_level="CRITICAL",
                        risk_category="OVERALL_QUALITY",
                        description=(
                            f"Table {domain.table_name} has critically low overall "
                            f"quality score ({quality.overall:.0%})"
                        ),
                        recommended_action=(
                            "Comprehensive data cleansing required before migration; consider phased migration approach"
                        ),
                        priority=1,
                    )
                )

        # Sort by priority (ascending = most urgent first)
        entries.sort(key=lambda e: e.priority)
        return entries
