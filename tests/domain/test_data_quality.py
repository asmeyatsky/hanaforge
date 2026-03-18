"""Tests for data quality domain logic — pure unit tests, no mocks."""

from datetime import datetime, timezone

import pytest

from domain.entities.data_domain import DataDomain
from domain.services.bp_consolidation_service import BPConsolidationService
from domain.services.data_quality_service import DataQualityService
from domain.services.universal_journal_service import UniversalJournalService
from domain.value_objects.data_quality import (
    DataMigrationStatus,
    DataQualityScore,
    FieldNullRate,
    TransformationRule,
    TransformationRuleType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_data_domain(
    *,
    table_name: str = "BKPF",
    record_count: int = 1000,
    field_count: int = 20,
    null_rates: tuple[FieldNullRate, ...] = (),
    duplicate_key_count: int = 0,
    referential_integrity_score: float = 1.0,
    encoding_issues: tuple[str, ...] = (),
    migration_status: DataMigrationStatus = DataMigrationStatus.NOT_PROFILED,
    quality_score: DataQualityScore | None = None,
) -> DataDomain:
    return DataDomain(
        id="dd-001",
        landscape_id="land-001",
        table_name=table_name,
        record_count=record_count,
        field_count=field_count,
        null_rates=null_rates,
        duplicate_key_count=duplicate_key_count,
        referential_integrity_score=referential_integrity_score,
        encoding_issues=encoding_issues,
        migration_status=migration_status,
        transformation_rules=(),
        quality_score=quality_score,
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# DataQualityScore tests
# ---------------------------------------------------------------------------


class TestDataQualityScoreCalculation:
    def test_perfect_quality_score(self) -> None:
        score = DataQualityScore(completeness=1.0, consistency=1.0, accuracy=1.0)

        assert score.overall == 1.0
        assert score.risk_level == "LOW"

    def test_weighted_average_calculation(self) -> None:
        score = DataQualityScore(completeness=0.8, consistency=0.6, accuracy=0.4)

        # 0.8*0.40 + 0.6*0.35 + 0.4*0.25 = 0.32 + 0.21 + 0.10 = 0.63
        assert abs(score.overall - 0.63) < 0.001
        # 0.63 is below the 0.65 MEDIUM threshold, so risk_level is HIGH
        assert score.risk_level == "HIGH"

    def test_critical_risk_level(self) -> None:
        score = DataQualityScore(completeness=0.1, consistency=0.2, accuracy=0.1)

        assert score.overall < 0.40
        assert score.risk_level == "CRITICAL"

    def test_high_risk_level(self) -> None:
        score = DataQualityScore(completeness=0.5, consistency=0.5, accuracy=0.5)

        assert score.overall == 0.5
        assert score.risk_level == "HIGH"

    def test_medium_risk_level(self) -> None:
        score = DataQualityScore(completeness=0.8, consistency=0.7, accuracy=0.6)

        # 0.8*0.40 + 0.7*0.35 + 0.6*0.25 = 0.32 + 0.245 + 0.15 = 0.715
        assert score.risk_level == "MEDIUM"

    def test_validation_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="completeness must be between 0 and 1"):
            DataQualityScore(completeness=1.5, consistency=0.5, accuracy=0.5)

        with pytest.raises(ValueError, match="consistency must be between 0 and 1"):
            DataQualityScore(completeness=0.5, consistency=-0.1, accuracy=0.5)


# ---------------------------------------------------------------------------
# FieldNullRate tests
# ---------------------------------------------------------------------------


class TestFieldNullRatePercentage:
    def test_zero_nulls(self) -> None:
        rate = FieldNullRate(field_name="BUKRS", null_count=0, total_count=1000)

        assert rate.null_percentage == 0.0

    def test_all_nulls(self) -> None:
        rate = FieldNullRate(field_name="BUKRS", null_count=1000, total_count=1000)

        assert rate.null_percentage == 100.0

    def test_partial_nulls(self) -> None:
        rate = FieldNullRate(field_name="BUKRS", null_count=250, total_count=1000)

        assert rate.null_percentage == 25.0

    def test_zero_total_returns_zero(self) -> None:
        rate = FieldNullRate(field_name="BUKRS", null_count=0, total_count=0)

        assert rate.null_percentage == 0.0

    def test_validation_rejects_negative_counts(self) -> None:
        with pytest.raises(ValueError, match="null_count cannot be negative"):
            FieldNullRate(field_name="BUKRS", null_count=-1, total_count=100)

    def test_validation_rejects_null_exceeding_total(self) -> None:
        with pytest.raises(ValueError, match="null_count.*cannot exceed total_count"):
            FieldNullRate(field_name="BUKRS", null_count=101, total_count=100)


# ---------------------------------------------------------------------------
# Risk register tests
# ---------------------------------------------------------------------------


class TestRiskRegisterPrioritisation:
    def test_unprofiled_table_gets_critical_priority(self) -> None:
        service = DataQualityService()
        domain = _make_data_domain()

        entries = service.generate_risk_register([domain])

        assert len(entries) >= 1
        assert entries[0].risk_level == "CRITICAL"
        assert entries[0].risk_category == "NOT_PROFILED"
        assert entries[0].priority == 1

    def test_duplicate_keys_generate_risk_entry(self) -> None:
        service = DataQualityService()
        quality = DataQualityScore(completeness=0.9, consistency=0.9, accuracy=0.9)
        domain = _make_data_domain(
            duplicate_key_count=50,
            migration_status=DataMigrationStatus.PROFILED,
            quality_score=quality,
        )

        entries = service.generate_risk_register([domain])

        dup_entries = [e for e in entries if e.risk_category == "DUPLICATE_KEYS"]
        assert len(dup_entries) == 1
        assert dup_entries[0].risk_level == "HIGH"

    def test_critical_duplicates_above_100(self) -> None:
        service = DataQualityService()
        quality = DataQualityScore(completeness=0.9, consistency=0.9, accuracy=0.9)
        domain = _make_data_domain(
            duplicate_key_count=150,
            migration_status=DataMigrationStatus.PROFILED,
            quality_score=quality,
        )

        entries = service.generate_risk_register([domain])

        dup_entries = [e for e in entries if e.risk_category == "DUPLICATE_KEYS"]
        assert dup_entries[0].risk_level == "CRITICAL"
        assert dup_entries[0].priority == 1

    def test_risk_entries_sorted_by_priority(self) -> None:
        service = DataQualityService()
        quality_low = DataQualityScore(completeness=0.3, consistency=0.5, accuracy=0.2)
        domain = _make_data_domain(
            duplicate_key_count=200,
            migration_status=DataMigrationStatus.PROFILED,
            quality_score=quality_low,
            encoding_issues=("Encoding issue in LIFNR",),
        )

        entries = service.generate_risk_register([domain])

        priorities = [e.priority for e in entries]
        assert priorities == sorted(priorities)

    def test_multiple_tables_combined_risk_register(self) -> None:
        service = DataQualityService()
        good_quality = DataQualityScore(completeness=0.95, consistency=0.9, accuracy=1.0)
        bad_quality = DataQualityScore(completeness=0.3, consistency=0.4, accuracy=0.2)

        domains = [
            _make_data_domain(
                table_name="BKPF",
                quality_score=good_quality,
                migration_status=DataMigrationStatus.PROFILED,
            ),
            _make_data_domain(
                table_name="BSEG",
                quality_score=bad_quality,
                migration_status=DataMigrationStatus.PROFILED,
            ),
        ]

        entries = service.generate_risk_register(domains)

        bseg_entries = [e for e in entries if e.table_name == "BSEG"]
        assert len(bseg_entries) > 0


# ---------------------------------------------------------------------------
# BP consolidation tests
# ---------------------------------------------------------------------------


class TestBPConsolidationDetection:
    def test_detects_matching_tax_ids(self) -> None:
        service = BPConsolidationService()
        customers = [
            {"id": "C001", "name": "Acme Corp", "tax_id": "DE123456789", "address": "Berlin"},
            {"id": "C002", "name": "Beta Ltd", "tax_id": "DE987654321", "address": "Munich"},
        ]
        vendors = [
            {"id": "V001", "name": "Acme Corporation", "tax_id": "DE123456789", "address": "Berlin"},
            {"id": "V002", "name": "Gamma AG", "tax_id": "DE555555555", "address": "Hamburg"},
        ]

        result = service.assess_consolidation(customers, vendors)

        assert result.customer_count == 2
        assert result.vendor_count == 2
        assert result.duplicate_pairs == 1
        assert ("C001", "V001") in result.merge_candidates

    def test_no_duplicates(self) -> None:
        service = BPConsolidationService()
        customers = [
            {"id": "C001", "name": "Acme Corp", "tax_id": "DE111", "address": "Berlin"},
        ]
        vendors = [
            {"id": "V001", "name": "Beta Ltd", "tax_id": "DE222", "address": "Munich"},
        ]

        result = service.assess_consolidation(customers, vendors)

        assert result.duplicate_pairs == 0
        assert result.consolidation_complexity == "LOW"

    def test_complexity_scales_with_duplicates(self) -> None:
        service = BPConsolidationService()
        # Create many matching pairs (>20% ratio)
        customers = [
            {"id": f"C{i:03d}", "name": f"Company {i}", "tax_id": f"DE{i:09d}", "address": "Berlin"} for i in range(10)
        ]
        vendors = [
            {"id": f"V{i:03d}", "name": f"Company {i}", "tax_id": f"DE{i:09d}", "address": "Berlin"} for i in range(10)
        ]

        result = service.assess_consolidation(customers, vendors)

        assert result.duplicate_pairs == 10
        assert result.consolidation_complexity == "HIGH"

    def test_empty_records(self) -> None:
        service = BPConsolidationService()

        result = service.assess_consolidation([], [])

        assert result.customer_count == 0
        assert result.vendor_count == 0
        assert result.duplicate_pairs == 0
        assert result.consolidation_complexity == "LOW"


# ---------------------------------------------------------------------------
# Universal Journal tests
# ---------------------------------------------------------------------------


class TestUniversalJournalAssessment:
    def test_standard_config_low_complexity(self) -> None:
        service = UniversalJournalService()
        fi_config = {
            "coding_blocks": ["BUKRS", "KOSTL", "PRCTR"],
            "profit_centres": ["PC001", "PC002"],
            "segment_reporting": [],
            "new_gl_active": True,
            "special_ledgers": False,
        }
        co_config = {
            "profit_centres": ["PC001", "PC003"],
        }

        result = service.assess_readiness(fi_config, co_config)

        assert len(result.custom_coding_blocks) == 0
        assert result.profit_centre_assignments == 3  # PC001, PC002, PC003
        assert result.segment_reporting_configs == 0
        assert result.migration_complexity == "LOW"

    def test_custom_coding_blocks_detected(self) -> None:
        service = UniversalJournalService()
        fi_config = {
            "coding_blocks": ["BUKRS", "ZCUSTOM1", "ZCUSTOM2", "PRCTR"],
            "profit_centres": [],
            "segment_reporting": [],
            "new_gl_active": True,
            "special_ledgers": False,
        }
        co_config = {"profit_centres": []}

        result = service.assess_readiness(fi_config, co_config)

        assert "ZCUSTOM1" in result.custom_coding_blocks
        assert "ZCUSTOM2" in result.custom_coding_blocks
        assert len(result.custom_coding_blocks) == 2

    def test_classic_gl_increases_complexity(self) -> None:
        service = UniversalJournalService()
        fi_config = {
            "coding_blocks": [],
            "profit_centres": [],
            "segment_reporting": [],
            "new_gl_active": False,
            "special_ledgers": True,
        }
        co_config = {"profit_centres": []}

        result = service.assess_readiness(fi_config, co_config)

        assert "HIGH" in result.fi_gl_simplification_impact
        assert result.migration_complexity in ("MEDIUM", "HIGH")

    def test_high_complexity_scenario(self) -> None:
        service = UniversalJournalService()
        fi_config = {
            "coding_blocks": [
                "BUKRS",
                "ZCUST1",
                "ZCUST2",
                "ZCUST3",
                "ZCUST4",
                "ZCUST5",
                "ZCUST6",
            ],
            "profit_centres": [f"PC{i:04d}" for i in range(500)],
            "segment_reporting": [f"SEG{i}" for i in range(15)],
            "new_gl_active": False,
            "special_ledgers": True,
        }
        co_config = {
            "profit_centres": [f"PC{i:04d}" for i in range(600)],
        }

        result = service.assess_readiness(fi_config, co_config)

        assert result.migration_complexity == "HIGH"
        assert len(result.custom_coding_blocks) == 6  # 6 custom blocks (not standard)


# ---------------------------------------------------------------------------
# DataDomain entity tests
# ---------------------------------------------------------------------------


class TestDataDomainProfileComplete:
    def test_profile_complete_transitions_status(self) -> None:
        domain = _make_data_domain()
        null_rates = (
            FieldNullRate(field_name="BUKRS", null_count=10, total_count=1000),
            FieldNullRate(field_name="BELNR", null_count=0, total_count=1000),
        )

        updated = domain.profile_complete(
            null_rates=null_rates,
            dup_count=5,
            ref_score=0.95,
            encoding_issues=(),
        )

        assert updated.migration_status == DataMigrationStatus.PROFILED
        assert updated.null_rates == null_rates
        assert updated.duplicate_key_count == 5
        assert updated.referential_integrity_score == 0.95
        assert updated.encoding_issues == ()

    def test_profile_complete_preserves_immutability(self) -> None:
        original = _make_data_domain()
        null_rates = (FieldNullRate(field_name="F1", null_count=0, total_count=100),)

        updated = original.profile_complete(
            null_rates=null_rates,
            dup_count=0,
            ref_score=1.0,
            encoding_issues=(),
        )

        assert original.migration_status == DataMigrationStatus.NOT_PROFILED
        assert updated.migration_status == DataMigrationStatus.PROFILED

    def test_add_transformation_rule(self) -> None:
        domain = _make_data_domain()
        rule = TransformationRule(
            source_field="KUNNR",
            target_field="PARTNER",
            rule_type=TransformationRuleType.LOOKUP,
            rule_expression="BP_LOOKUP(KUNNR)",
            description="Map customer number to Business Partner",
        )

        updated = domain.add_transformation_rule(rule)

        assert len(updated.transformation_rules) == 1
        assert updated.transformation_rules[0].source_field == "KUNNR"
        assert len(domain.transformation_rules) == 0  # original unchanged

    def test_mark_migration_ready_from_profiled(self) -> None:
        domain = _make_data_domain(migration_status=DataMigrationStatus.PROFILED)

        updated = domain.mark_migration_ready()

        assert updated.migration_status == DataMigrationStatus.TRANSFORMATION_READY

    def test_mark_migration_ready_from_cleansed(self) -> None:
        domain = _make_data_domain(migration_status=DataMigrationStatus.CLEANSED)

        updated = domain.mark_migration_ready()

        assert updated.migration_status == DataMigrationStatus.TRANSFORMATION_READY

    def test_cannot_mark_ready_from_not_profiled(self) -> None:
        domain = _make_data_domain(migration_status=DataMigrationStatus.NOT_PROFILED)

        with pytest.raises(ValueError, match="Cannot mark migration ready"):
            domain.mark_migration_ready()

    def test_profile_complete_rejects_invalid_ref_score(self) -> None:
        domain = _make_data_domain()

        with pytest.raises(ValueError, match="referential_integrity_score must be between"):
            domain.profile_complete(
                null_rates=(),
                dup_count=0,
                ref_score=1.5,
                encoding_issues=(),
            )
