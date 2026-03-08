"""Tests for the CustomObject entity — pure domain logic, no mocks."""

import pytest

from domain.entities.custom_object import CustomObject
from domain.events.analysis_events import ObjectAnalysedEvent
from domain.value_objects.effort_points import EffortPoints
from domain.value_objects.object_type import (
    ABAPObjectType,
    BusinessDomain,
    CompatibilityStatus,
    RemediationStatus,
)


def _make_object(
    *,
    compatibility_status: CompatibilityStatus = CompatibilityStatus.UNKNOWN,
    remediation_status: RemediationStatus = RemediationStatus.NOT_STARTED,
    complexity_score: EffortPoints | None = None,
) -> CustomObject:
    return CustomObject(
        id="obj-001",
        landscape_id="land-001",
        object_type=ABAPObjectType.PROGRAM,
        object_name="ZFI_PAYMENT_PROC",
        package_name="ZFI",
        domain=BusinessDomain.FI,
        complexity_score=complexity_score,
        compatibility_status=compatibility_status,
        remediation_status=remediation_status,
        source_code="REPORT ZFI_PAYMENT_PROC.",
        deprecated_apis=(),
    )


class TestMarkAsIncompatible:
    def test_mark_as_incompatible(self) -> None:
        obj = _make_object()
        deprecated = ("BSEG direct access", "READ TABLE ... INTO wa")

        updated = obj.mark_as_incompatible(deprecated)

        assert updated.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert updated.deprecated_apis == deprecated
        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, ObjectAnalysedEvent)
        assert event.object_name == "ZFI_PAYMENT_PROC"
        assert event.compatibility_status == "INCOMPATIBLE"


class TestRemediation:
    def test_start_remediation_from_incompatible(self) -> None:
        obj = _make_object(compatibility_status=CompatibilityStatus.INCOMPATIBLE)

        updated = obj.start_remediation()

        assert updated.remediation_status == RemediationStatus.IN_PROGRESS

    def test_start_remediation_rejects_non_incompatible(self) -> None:
        obj = _make_object(compatibility_status=CompatibilityStatus.COMPATIBLE)

        with pytest.raises(ValueError, match="Cannot start remediation"):
            obj.start_remediation()

    def test_complete_remediation(self) -> None:
        obj = _make_object(
            compatibility_status=CompatibilityStatus.INCOMPATIBLE,
            remediation_status=RemediationStatus.IN_PROGRESS,
        )

        updated = obj.complete_remediation()

        assert updated.remediation_status == RemediationStatus.REMEDIATED

    def test_complete_remediation_rejects_not_in_progress(self) -> None:
        obj = _make_object(
            compatibility_status=CompatibilityStatus.INCOMPATIBLE,
            remediation_status=RemediationStatus.NOT_STARTED,
        )

        with pytest.raises(ValueError, match="Cannot complete remediation"):
            obj.complete_remediation()


class TestComplexityScoring:
    def test_score_complexity_validates_range(self) -> None:
        obj = _make_object()
        points = EffortPoints(points=3, description="Medium effort")

        updated = obj.score_complexity(points)

        assert updated.complexity_score is not None
        assert updated.complexity_score.points == 3

    def test_score_complexity_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="points must be between 1 and 5"):
            EffortPoints(points=0, description="Invalid")

        with pytest.raises(ValueError, match="points must be between 1 and 5"):
            EffortPoints(points=6, description="Invalid")


class TestImmutability:
    def test_custom_object_is_immutable(self) -> None:
        original = _make_object()

        updated = original.mark_as_incompatible(("BSEG access",))

        # Original unchanged
        assert original.compatibility_status == CompatibilityStatus.UNKNOWN
        assert original.deprecated_apis == ()
        assert original.domain_events == ()

        # Updated reflects new state
        assert updated.compatibility_status == CompatibilityStatus.INCOMPATIBLE
        assert len(updated.deprecated_apis) == 1
        assert len(updated.domain_events) == 1
