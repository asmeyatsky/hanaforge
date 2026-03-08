"""Tests for the ComplexityScoringService — pure domain logic, no mocks."""

from datetime import datetime, timezone

from domain.entities.custom_object import CustomObject
from domain.entities.sap_landscape import SAPLandscape
from domain.services.complexity_scoring_service import ComplexityScoringService
from domain.value_objects.object_type import (
    ABAPObjectType,
    BusinessDomain,
    CompatibilityStatus,
    RemediationStatus,
    SystemRole,
)


def _make_landscape(
    *,
    custom_object_count: int = 100,
    db_size_gb: float = 50.0,
    number_of_users: int = 50,
) -> SAPLandscape:
    return SAPLandscape(
        id="land-001",
        programme_id="prog-001",
        system_id="PRD",
        system_role=SystemRole.PRD,
        db_size_gb=db_size_gb,
        number_of_users=number_of_users,
        custom_object_count=custom_object_count,
        integration_points=(),
        created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


def _make_objects(
    count: int,
    *,
    incompatible_count: int = 0,
) -> list[CustomObject]:
    objects: list[CustomObject] = []
    for i in range(count):
        status = (
            CompatibilityStatus.INCOMPATIBLE
            if i < incompatible_count
            else CompatibilityStatus.COMPATIBLE
        )
        objects.append(
            CustomObject(
                id=f"obj-{i:04d}",
                landscape_id="land-001",
                object_type=ABAPObjectType.PROGRAM,
                object_name=f"ZPROG_{i:04d}",
                package_name="ZTEST",
                domain=BusinessDomain.FI,
                complexity_score=None,
                compatibility_status=status,
                remediation_status=RemediationStatus.NOT_STARTED,
                source_code=f"REPORT ZPROG_{i:04d}.",
                deprecated_apis=(),
            )
        )
    return objects


class TestComplexityScoringService:
    def test_low_complexity_landscape(self) -> None:
        service = ComplexityScoringService()
        landscape = _make_landscape(
            custom_object_count=50,
            db_size_gb=30.0,
            number_of_users=20,
        )
        objects = _make_objects(10, incompatible_count=0)

        score = service.calculate_landscape_complexity(landscape, objects)

        assert score.score <= 25
        assert score.risk_level == "LOW"

    def test_high_complexity_landscape(self) -> None:
        service = ComplexityScoringService()
        landscape = _make_landscape(
            custom_object_count=6000,
            db_size_gb=12000.0,
            number_of_users=15000,
        )
        objects = _make_objects(100, incompatible_count=80)

        score = service.calculate_landscape_complexity(landscape, objects)

        assert score.score >= 75
        assert score.risk_level in ("HIGH", "CRITICAL")

    def test_score_with_no_objects(self) -> None:
        service = ComplexityScoringService()
        landscape = _make_landscape(
            custom_object_count=50,
            db_size_gb=30.0,
            number_of_users=20,
        )
        objects: list[CustomObject] = []

        score = service.calculate_landscape_complexity(landscape, objects)

        # With no objects the incompatible ratio returns 10.0 (low)
        assert 1 <= score.score <= 100

    def test_score_boundaries(self) -> None:
        service = ComplexityScoringService()

        # Minimum possible inputs
        landscape_min = _make_landscape(
            custom_object_count=0,
            db_size_gb=0.0,
            number_of_users=0,
        )
        score_min = service.calculate_landscape_complexity(landscape_min, [])
        assert score_min.score >= 1

        # Maximum possible inputs
        landscape_max = _make_landscape(
            custom_object_count=100_000,
            db_size_gb=100_000.0,
            number_of_users=100_000,
        )
        all_incompatible = _make_objects(100, incompatible_count=100)
        score_max = service.calculate_landscape_complexity(
            landscape_max, all_incompatible
        )
        assert score_max.score <= 100
