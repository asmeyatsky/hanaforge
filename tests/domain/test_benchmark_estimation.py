"""Tests for BenchmarkEstimationService — pure domain logic, no mocks."""

from datetime import datetime, timezone

from domain.entities.benchmark_entry import BenchmarkEntry
from domain.entities.programme import Programme
from domain.services.benchmark_estimation_service import BenchmarkEstimationService
from domain.value_objects.complexity_score import ComplexityScore
from domain.value_objects.object_type import ProgrammeStatus


def _make_programme(
    *,
    source_version: str = "ECC 6.0 EHP8",
    target_version: str = "S/4HANA 2023",
    complexity_score: int | None = None,
) -> Programme:
    cs = ComplexityScore(score=complexity_score) if complexity_score else None
    return Programme(
        id="prog-001",
        name="Test Migration Programme",
        customer_id="cust-001",
        sap_source_version=source_version,
        target_version=target_version,
        go_live_date=None,
        status=ProgrammeStatus.CREATED,
        complexity_score=cs,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _make_benchmark(
    *,
    id: str = "bench-test-001",
    source_version: str = "ECC 6.0 EHP8",
    target_version: str = "S/4HANA 2023",
    db_size_gb: float = 500.0,
    custom_object_count: int = 1500,
    duration_days: int = 200,
    team_size: int = 15,
    complexity_score: int = 50,
    industry: str = "Manufacturing",
    region: str = "Europe",
    success: bool = True,
) -> BenchmarkEntry:
    return BenchmarkEntry(
        id=id,
        source_version=source_version,
        target_version=target_version,
        db_size_gb=db_size_gb,
        custom_object_count=custom_object_count,
        duration_days=duration_days,
        team_size=team_size,
        complexity_score=complexity_score,
        industry=industry,
        region=region,
        success=success,
        lessons_learned=("Test lesson",),
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


class TestBenchmarkEstimationService:
    """Unit tests for the benchmark estimation domain service."""

    def test_empty_benchmarks_returns_zero_estimate(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme()

        result = service.estimate_duration(programme, [])

        assert result.estimated_duration_days == 0.0
        assert result.confidence_level == 0.0
        assert result.sample_size == 0
        assert result.comparable_projects == 0
        assert len(result.risk_factors) > 0

    def test_single_exact_match(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme(
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
        )
        benchmark = _make_benchmark(
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
            duration_days=180,
            db_size_gb=500.0,
            custom_object_count=1500,
            complexity_score=50,
        )

        result = service.estimate_duration(
            programme,
            [benchmark],
            db_size_gb=500.0,
            custom_object_count=1500,
            complexity_score=50,
        )

        # With a single perfect match, estimated duration should be ~180
        assert result.estimated_duration_days == 180.0
        assert result.sample_size == 1

    def test_weighted_average_of_multiple_benchmarks(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme(
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
            complexity_score=50,
        )

        # Two benchmarks: one exact match, one partial match
        exact_match = _make_benchmark(
            id="bench-exact",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
            duration_days=200,
            db_size_gb=500.0,
            custom_object_count=1500,
            complexity_score=50,
        )
        partial_match = _make_benchmark(
            id="bench-partial",
            source_version="ECC 6.0 EHP7",
            target_version="S/4HANA 2022",
            duration_days=300,
            db_size_gb=1500.0,
            custom_object_count=3000,
            complexity_score=70,
        )

        result = service.estimate_duration(
            programme,
            [exact_match, partial_match],
            db_size_gb=500.0,
            custom_object_count=1500,
            complexity_score=50,
        )

        # The exact match should pull the estimate closer to 200 than 300
        assert result.estimated_duration_days < 260
        assert result.sample_size == 2

    def test_confidence_increases_with_more_samples(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme()

        # Single benchmark
        single_result = service.estimate_duration(
            programme,
            [_make_benchmark(id="b1")],
            db_size_gb=500.0,
            custom_object_count=1500,
        )

        # Multiple benchmarks with varying parameters
        many_benchmarks = [
            _make_benchmark(id=f"b{i}", duration_days=150 + i * 10, complexity_score=max(1, 40 + i * 5))
            for i in range(10)
        ]
        many_result = service.estimate_duration(
            programme,
            many_benchmarks,
            db_size_gb=500.0,
            custom_object_count=1500,
        )

        assert many_result.confidence_level >= single_result.confidence_level

    def test_confidence_intervals_are_ordered(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme()

        benchmarks = [
            _make_benchmark(id=f"b{i}", duration_days=100 + i * 30)
            for i in range(8)
        ]

        result = service.estimate_duration(
            programme,
            benchmarks,
            db_size_gb=500.0,
            custom_object_count=1500,
        )

        assert result.lower_bound_days <= result.estimated_duration_days
        assert result.estimated_duration_days <= result.upper_bound_days

    def test_risk_factors_for_large_database(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme()
        benchmark = _make_benchmark(db_size_gb=6000.0)

        result = service.estimate_duration(
            programme,
            [benchmark],
            db_size_gb=6000.0,
            custom_object_count=1500,
        )

        assert any("database" in rf.lower() for rf in result.risk_factors)

    def test_risk_factors_for_high_custom_object_count(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme()
        benchmark = _make_benchmark(custom_object_count=4000)

        result = service.estimate_duration(
            programme,
            [benchmark],
            db_size_gb=500.0,
            custom_object_count=4000,
        )

        assert any("custom object" in rf.lower() for rf in result.risk_factors)

    def test_risk_factors_for_ecc_to_s4_jump(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme(
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
        )
        benchmark = _make_benchmark()

        result = service.estimate_duration(
            programme,
            [benchmark],
            db_size_gb=500.0,
            custom_object_count=1500,
        )

        assert any("version jump" in rf.lower() for rf in result.risk_factors)

    def test_risk_factors_for_high_failure_rate(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme()

        # Majority of benchmarks are failures
        benchmarks = [
            _make_benchmark(id=f"b{i}", success=(i < 2))
            for i in range(6)
        ]

        result = service.estimate_duration(
            programme,
            benchmarks,
            db_size_gb=500.0,
            custom_object_count=1500,
        )

        assert any("failure rate" in rf.lower() for rf in result.risk_factors)

    def test_version_similarity_scoring(self) -> None:
        service = BenchmarkEstimationService()

        # Exact version match should produce higher similarity
        assert service._version_similarity(
            "ECC 6.0 EHP8", "S/4HANA 2023",
            "ECC 6.0 EHP8", "S/4HANA 2023",
        ) == 1.0

        # Partial match (target only)
        assert service._version_similarity(
            "ECC 6.0 EHP8", "S/4HANA 2023",
            "ECC 6.0 EHP7", "S/4HANA 2023",
        ) == 0.5

        # No match
        assert service._version_similarity(
            "ECC 6.0 EHP8", "S/4HANA 2023",
            "ECC 6.0 EHP6", "S/4HANA 2021",
        ) == 0.0

    def test_numeric_similarity_scoring(self) -> None:
        service = BenchmarkEstimationService()

        # Identical values
        assert service._numeric_similarity(500.0, 500.0) == 1.0

        # Both zero
        assert service._numeric_similarity(0.0, 0.0) == 1.0

        # Proportional difference
        sim_close = service._numeric_similarity(500.0, 600.0)
        sim_far = service._numeric_similarity(500.0, 2000.0)
        assert sim_close > sim_far

    def test_estimation_with_complexity_score(self) -> None:
        service = BenchmarkEstimationService()
        programme = _make_programme(complexity_score=70)

        # Benchmark with similar complexity should weight higher
        similar = _make_benchmark(
            id="b-similar",
            complexity_score=65,
            duration_days=200,
        )
        different = _make_benchmark(
            id="b-different",
            complexity_score=20,
            duration_days=100,
        )

        result = service.estimate_duration(
            programme,
            [similar, different],
            db_size_gb=500.0,
            custom_object_count=1500,
            complexity_score=70,
        )

        # Estimate should be closer to the similar benchmark (200 days)
        assert result.estimated_duration_days > 140

    def test_percentile_computation(self) -> None:
        service = BenchmarkEstimationService()

        # Test with known values
        values = [100, 200, 300, 400, 500]
        assert service._percentile(values, 0) == 100.0
        assert service._percentile(values, 50) == 300.0
        assert service._percentile(values, 100) == 500.0

        # Single value
        assert service._percentile([42], 50) == 42.0

        # Empty list
        assert service._percentile([], 50) == 0.0

    def test_estimate_result_invariants(self) -> None:
        """All estimation results must satisfy basic invariants."""
        service = BenchmarkEstimationService()
        programme = _make_programme()

        benchmarks = [
            _make_benchmark(id=f"b{i}", duration_days=100 + i * 25)
            for i in range(15)
        ]

        result = service.estimate_duration(
            programme,
            benchmarks,
            db_size_gb=800.0,
            custom_object_count=2000,
        )

        # Invariants
        assert result.estimated_duration_days >= 0
        assert 0.0 <= result.confidence_level <= 1.0
        assert result.lower_bound_days <= result.estimated_duration_days
        assert result.upper_bound_days >= result.estimated_duration_days
        assert result.sample_size > 0
        assert result.comparable_projects >= 0
        assert result.comparable_projects <= result.sample_size
