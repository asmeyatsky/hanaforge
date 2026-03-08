"""Tests for the Programme aggregate root — pure domain logic, no mocks."""

from datetime import datetime, timezone

import pytest

from domain.entities.programme import Programme
from domain.events.programme_events import (
    AnalysisStartedEvent,
    DiscoveryCompletedEvent,
    DiscoveryStartedEvent,
)
from domain.value_objects.complexity_score import ComplexityScore
from domain.value_objects.object_type import ProgrammeStatus


def _make_programme(
    *,
    status: ProgrammeStatus = ProgrammeStatus.CREATED,
    complexity_score: ComplexityScore | None = None,
) -> Programme:
    return Programme(
        id="prog-001",
        name="Acme ECC Migration",
        customer_id="ACME-001",
        sap_source_version="ECC 6.0",
        target_version="S/4HANA 2023",
        go_live_date=None,
        status=status,
        complexity_score=complexity_score,
        created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestCreateProgramme:
    def test_create_programme_with_valid_data(self) -> None:
        prog = _make_programme()

        assert prog.id == "prog-001"
        assert prog.name == "Acme ECC Migration"
        assert prog.customer_id == "ACME-001"
        assert prog.sap_source_version == "ECC 6.0"
        assert prog.target_version == "S/4HANA 2023"
        assert prog.status == ProgrammeStatus.CREATED
        assert prog.complexity_score is None
        assert prog.domain_events == ()


class TestStartDiscovery:
    def test_start_discovery_changes_status(self) -> None:
        prog = _make_programme()

        updated = prog.start_discovery()

        assert updated.status == ProgrammeStatus.DISCOVERY_IN_PROGRESS

    def test_start_discovery_emits_event(self) -> None:
        prog = _make_programme()

        updated = prog.start_discovery()

        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, DiscoveryStartedEvent)
        assert event.aggregate_id == "prog-001"


class TestCompleteDiscovery:
    def test_complete_discovery_sets_complexity(self) -> None:
        prog = _make_programme(status=ProgrammeStatus.DISCOVERY_IN_PROGRESS)
        score = ComplexityScore(score=67)

        updated = prog.complete_discovery(score)

        assert updated.status == ProgrammeStatus.DISCOVERY_COMPLETE
        assert updated.complexity_score is not None
        assert updated.complexity_score.score == 67
        assert updated.complexity_score.risk_level == "HIGH"

        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, DiscoveryCompletedEvent)
        assert event.complexity_score == 67


class TestStartAnalysis:
    def test_start_analysis_from_discovery_complete(self) -> None:
        prog = _make_programme(status=ProgrammeStatus.DISCOVERY_COMPLETE)

        updated = prog.start_analysis()

        assert updated.status == ProgrammeStatus.ANALYSIS_IN_PROGRESS
        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, AnalysisStartedEvent)

    def test_cannot_start_analysis_before_discovery(self) -> None:
        prog = _make_programme(status=ProgrammeStatus.CREATED)

        with pytest.raises(ValueError, match="Invalid status transition"):
            prog.start_analysis()


class TestImmutability:
    def test_programme_is_immutable(self) -> None:
        original = _make_programme()

        updated = original.start_discovery()

        # Original must remain unchanged
        assert original.status == ProgrammeStatus.CREATED
        assert original.domain_events == ()

        # Updated reflects the new state
        assert updated.status == ProgrammeStatus.DISCOVERY_IN_PROGRESS
        assert len(updated.domain_events) == 1
