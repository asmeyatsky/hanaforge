"""Tests for CreateProgrammeUseCase — mocked ports only."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from application.commands.create_programme import CreateProgrammeUseCase
from application.dtos.programme_dto import CreateProgrammeRequest
from domain.events.programme_events import ProgrammeCreatedEvent
from domain.value_objects.object_type import ProgrammeStatus


@pytest.fixture()
def mock_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def mock_event_bus() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def use_case(mock_repo: AsyncMock, mock_event_bus: AsyncMock) -> CreateProgrammeUseCase:
    return CreateProgrammeUseCase(
        repository=mock_repo,
        event_bus=mock_event_bus,
    )


@pytest.fixture()
def valid_request() -> CreateProgrammeRequest:
    return CreateProgrammeRequest(
        name="Acme ECC Migration",
        customer_id="ACME-001",
        sap_source_version="ECC 6.0",
        target_version="S/4HANA 2023",
        go_live_date=None,
    )


class TestCreateProgrammeUseCase:
    @pytest.mark.asyncio
    async def test_creates_and_saves_programme(
        self,
        use_case: CreateProgrammeUseCase,
        mock_repo: AsyncMock,
        valid_request: CreateProgrammeRequest,
    ) -> None:
        await use_case.execute(valid_request)

        mock_repo.save.assert_awaited_once()
        saved_programme = mock_repo.save.call_args[0][0]
        assert saved_programme.name == "Acme ECC Migration"
        assert saved_programme.customer_id == "ACME-001"
        assert saved_programme.status == ProgrammeStatus.CREATED

    @pytest.mark.asyncio
    async def test_publishes_created_event(
        self,
        use_case: CreateProgrammeUseCase,
        mock_event_bus: AsyncMock,
        valid_request: CreateProgrammeRequest,
    ) -> None:
        await use_case.execute(valid_request)

        mock_event_bus.publish.assert_awaited_once()
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, ProgrammeCreatedEvent)
        assert published_event.programme_name == "Acme ECC Migration"
        assert published_event.customer_id == "ACME-001"

    @pytest.mark.asyncio
    async def test_returns_programme_response(
        self,
        use_case: CreateProgrammeUseCase,
        valid_request: CreateProgrammeRequest,
    ) -> None:
        response = await use_case.execute(valid_request)

        assert response.name == "Acme ECC Migration"
        assert response.customer_id == "ACME-001"
        assert response.sap_source_version == "ECC 6.0"
        assert response.target_version == "S/4HANA 2023"
        assert response.status == "CREATED"
        assert response.id  # UUID was generated
        assert response.created_at  # Timestamp was set
