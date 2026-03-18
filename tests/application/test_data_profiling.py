"""Tests for RunDataProfilingUseCase — mocked ports, verifying orchestration logic."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from application.commands.run_data_profiling import RunDataProfilingUseCase
from domain.entities.data_domain import DataDomain
from domain.events.data_events import DataProfilingCompletedEvent
from domain.ports.data_analysis_ports import ProfileResult
from domain.services.data_quality_service import DataQualityService
from domain.value_objects.data_quality import (
    DataMigrationStatus,
    FieldNullRate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_data_domain(
    domain_id: str,
    table_name: str,
) -> DataDomain:
    return DataDomain(
        id=domain_id,
        landscape_id="land-001",
        table_name=table_name,
        record_count=0,
        field_count=0,
        null_rates=(),
        duplicate_key_count=0,
        referential_integrity_score=0.0,
        encoding_issues=(),
        migration_status=DataMigrationStatus.NOT_PROFILED,
        transformation_rules=(),
        quality_score=None,
        created_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    )


def _make_profile_result(
    *,
    record_count: int = 500,
    field_count: int = 10,
    null_count: int = 50,
    dup_keys: int = 3,
    encoding_issues: tuple[str, ...] = (),
) -> ProfileResult:
    null_rates = tuple(
        FieldNullRate(
            field_name=f"FIELD_{i}",
            null_count=null_count if i == 0 else 0,
            total_count=record_count,
        )
        for i in range(field_count)
    )
    return ProfileResult(
        record_count=record_count,
        field_count=field_count,
        null_rates=null_rates,
        duplicate_keys=dup_keys,
        encoding_issues=encoding_issues,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def domains() -> list[DataDomain]:
    return [
        _make_data_domain("dd-001", "BKPF"),
        _make_data_domain("dd-002", "BSEG"),
        _make_data_domain("dd-003", "KNA1"),
    ]


@pytest.fixture()
def mock_data_repo(domains: list[DataDomain]) -> AsyncMock:
    repo = AsyncMock()
    repo.list_by_landscape = AsyncMock(return_value=domains)
    repo.save = AsyncMock()
    return repo


@pytest.fixture()
def mock_profiling_port() -> AsyncMock:
    """Returns different profile results per call to simulate varied data quality."""
    port = AsyncMock()
    results = [
        _make_profile_result(record_count=1000, field_count=15, null_count=10, dup_keys=0),
        _make_profile_result(record_count=5000, field_count=30, null_count=500, dup_keys=25),
        _make_profile_result(
            record_count=200,
            field_count=8,
            null_count=5,
            dup_keys=0,
            encoding_issues=("Encoding issue in NAME1",),
        ),
    ]
    port.profile_table = AsyncMock(side_effect=results)
    return port


@pytest.fixture()
def quality_service() -> DataQualityService:
    return DataQualityService()


@pytest.fixture()
def mock_event_bus() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def use_case(
    mock_data_repo: AsyncMock,
    mock_profiling_port: AsyncMock,
    quality_service: DataQualityService,
    mock_event_bus: AsyncMock,
) -> RunDataProfilingUseCase:
    return RunDataProfilingUseCase(
        data_repo=mock_data_repo,
        profiling_port=mock_profiling_port,
        quality_service=quality_service,
        event_bus=mock_event_bus,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunDataProfilingUseCase:
    @pytest.mark.asyncio
    async def test_profiles_all_tables_in_parallel(
        self,
        use_case: RunDataProfilingUseCase,
        mock_profiling_port: AsyncMock,
        domains: list[DataDomain],
    ) -> None:
        await use_case.execute(landscape_id="land-001")

        # Profiling port should be called once per domain
        assert mock_profiling_port.profile_table.await_count == len(domains)

    @pytest.mark.asyncio
    async def test_calculates_quality_scores(
        self,
        use_case: RunDataProfilingUseCase,
    ) -> None:
        result = await use_case.execute(landscape_id="land-001")

        # All 3 tables should be profiled
        assert result.tables_profiled == 3
        assert result.total_tables == 3

        # Overall quality should be non-zero
        assert result.overall_quality > 0.0

        # Each domain should have a quality score
        for domain_response in result.domains:
            assert domain_response.quality_score is not None
            assert "completeness" in domain_response.quality_score
            assert "consistency" in domain_response.quality_score
            assert "accuracy" in domain_response.quality_score
            assert "overall" in domain_response.quality_score
            assert "risk_level" in domain_response.quality_score

    @pytest.mark.asyncio
    async def test_publishes_profiling_completed_event(
        self,
        use_case: RunDataProfilingUseCase,
        mock_event_bus: AsyncMock,
    ) -> None:
        await use_case.execute(landscape_id="land-001")

        # Should publish both started and completed events
        assert mock_event_bus.publish.await_count == 2

        # The second call should be the completed event
        completed_event = mock_event_bus.publish.call_args_list[1][0][0]
        assert isinstance(completed_event, DataProfilingCompletedEvent)
        assert completed_event.landscape_id == "land-001"
        assert completed_event.tables_profiled == 3
        assert completed_event.overall_quality > 0.0

    @pytest.mark.asyncio
    async def test_saves_all_profiled_domains(
        self,
        use_case: RunDataProfilingUseCase,
        mock_data_repo: AsyncMock,
        domains: list[DataDomain],
    ) -> None:
        await use_case.execute(landscape_id="land-001")

        # Each domain should be saved after profiling
        assert mock_data_repo.save.await_count == len(domains)

    @pytest.mark.asyncio
    async def test_generates_risk_register(
        self,
        use_case: RunDataProfilingUseCase,
    ) -> None:
        result = await use_case.execute(landscape_id="land-001")

        # Risk register should be populated (at least for the domain with duplicates)
        assert isinstance(result.risk_register, list)

        # Check that risk entries have the expected structure
        for entry in result.risk_register:
            assert "table_name" in entry
            assert "risk_level" in entry
            assert "risk_category" in entry
            assert "description" in entry
            assert "recommended_action" in entry
            assert "priority" in entry

    @pytest.mark.asyncio
    async def test_empty_landscape_returns_empty_result(
        self,
        mock_profiling_port: AsyncMock,
        quality_service: DataQualityService,
        mock_event_bus: AsyncMock,
    ) -> None:
        empty_repo = AsyncMock()
        empty_repo.list_by_landscape = AsyncMock(return_value=[])

        use_case = RunDataProfilingUseCase(
            data_repo=empty_repo,
            profiling_port=mock_profiling_port,
            quality_service=quality_service,
            event_bus=mock_event_bus,
        )

        result = await use_case.execute(landscape_id="land-empty")

        assert result.total_tables == 0
        assert result.tables_profiled == 0
        assert result.overall_quality == 0.0
        assert result.risk_level == "CRITICAL"
        assert result.domains == []
