"""Tests for RunABAPAnalysisUseCase — mocked ports, verifying orchestration logic."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from application.commands.run_abap_analysis import RunABAPAnalysisUseCase
from domain.entities.custom_object import CustomObject
from domain.events.programme_events import AnalysisCompletedEvent
from domain.value_objects.object_type import (
    ABAPObjectType,
    BusinessDomain,
    CompatibilityStatus,
    RemediationStatus,
)

# ---------------------------------------------------------------------------
# Lightweight stub for the AI analysis result.
# The real AnalysisResult from domain.ports is a frozen dataclass; we replicate
# the attributes the use-case accesses so the test stays decoupled from infra.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FakeAnalysisResult:
    compatibility_status: str
    deprecated_apis: list[str]
    suggested_replacement: str | None = None
    issue_type: str | None = None
    deprecated_api: str | None = None
    generated_code: str | None = None
    confidence_score: float = 0.9
    effort_points: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_object(
    object_id: str,
    name: str,
    *,
    compat: CompatibilityStatus = CompatibilityStatus.UNKNOWN,
) -> CustomObject:
    return CustomObject(
        id=object_id,
        landscape_id="land-001",
        object_type=ABAPObjectType.PROGRAM,
        object_name=name,
        package_name="ZTEST",
        domain=BusinessDomain.FI,
        complexity_score=None,
        compatibility_status=compat,
        remediation_status=RemediationStatus.NOT_STARTED,
        source_code=f"REPORT {name}.",
        deprecated_apis=(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def objects() -> list[CustomObject]:
    return [
        _make_object("obj-001", "ZFI_PAYMENT"),
        _make_object("obj-002", "ZSD_ORDER"),
        _make_object("obj-003", "ZMM_STOCK"),
    ]


@pytest.fixture()
def mock_object_repo(objects: list[CustomObject]) -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_landscape = AsyncMock(return_value=objects)
    return repo


@pytest.fixture()
def mock_remediation_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.save_batch = AsyncMock()
    return repo


@pytest.fixture()
def mock_ai_analysis() -> AsyncMock:
    """Returns different results per call to simulate mixed compatibility."""
    ai = AsyncMock()

    results = [
        _FakeAnalysisResult(
            compatibility_status="COMPATIBLE",
            deprecated_apis=[],
        ),
        _FakeAnalysisResult(
            compatibility_status="INCOMPATIBLE",
            deprecated_apis=["BSEG direct access"],
            suggested_replacement="Use CDS view I_JournalEntry",
            issue_type="deprecated_api",
            deprecated_api="BSEG",
            generated_code="SELECT * FROM I_JournalEntry ...",
            confidence_score=0.92,
            effort_points=3,
        ),
        _FakeAnalysisResult(
            compatibility_status="NEEDS_REVIEW",
            deprecated_apis=["KONV access"],
        ),
    ]
    ai.analyze_object = AsyncMock(side_effect=results)
    return ai


@pytest.fixture()
def mock_event_bus() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def use_case(
    mock_object_repo: AsyncMock,
    mock_remediation_repo: AsyncMock,
    mock_ai_analysis: AsyncMock,
    mock_event_bus: AsyncMock,
) -> RunABAPAnalysisUseCase:
    return RunABAPAnalysisUseCase(
        object_repo=mock_object_repo,
        remediation_repo=mock_remediation_repo,
        ai_analysis=mock_ai_analysis,
        event_bus=mock_event_bus,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunABAPAnalysisUseCase:
    @pytest.mark.asyncio
    async def test_analyzes_all_objects(
        self,
        use_case: RunABAPAnalysisUseCase,
        mock_ai_analysis: AsyncMock,
        objects: list[CustomObject],
    ) -> None:
        await use_case.execute(landscape_id="land-001", programme_id="prog-001")

        assert mock_ai_analysis.analyze_object.await_count == len(objects)

    @pytest.mark.asyncio
    async def test_creates_remediations_for_incompatible(
        self,
        use_case: RunABAPAnalysisUseCase,
        mock_remediation_repo: AsyncMock,
    ) -> None:
        await use_case.execute(landscape_id="land-001", programme_id="prog-001")

        # Only 1 out of 3 objects is INCOMPATIBLE with a suggested_replacement
        mock_remediation_repo.save_batch.assert_awaited_once()
        saved_suggestions = mock_remediation_repo.save_batch.call_args[0][0]
        assert len(saved_suggestions) == 1
        assert saved_suggestions[0].object_id == "obj-002"

    @pytest.mark.asyncio
    async def test_returns_correct_counts(
        self,
        use_case: RunABAPAnalysisUseCase,
    ) -> None:
        result = await use_case.execute(landscape_id="land-001", programme_id="prog-001")

        assert result.total_objects == 3
        assert result.compatible_count == 1
        assert result.incompatible_count == 1
        assert result.needs_review_count == 1
        assert len(result.objects) == 3

    @pytest.mark.asyncio
    async def test_publishes_analysis_completed_event(
        self,
        use_case: RunABAPAnalysisUseCase,
        mock_event_bus: AsyncMock,
    ) -> None:
        await use_case.execute(landscape_id="land-001", programme_id="prog-001")

        mock_event_bus.publish.assert_awaited_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, AnalysisCompletedEvent)
        assert event.aggregate_id == "prog-001"
        assert event.compatible_count == 1
        assert event.incompatible_count == 1
