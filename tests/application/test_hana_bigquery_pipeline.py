"""Application-layer tests for HANA → BigQuery pipelines."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.commands.create_data_pipeline import CreateDataPipelineUseCase
from application.commands.start_pipeline_run import StartPipelineRunUseCase
from application.dtos.hana_bq_dto import CreateDataPipelineRequest, StartPipelineRunRequest, TableMappingRequest
from domain.entities.data_pipeline import DataPipeline
from domain.entities.sap_landscape import SAPLandscape
from domain.value_objects.hana_bq_types import ReplicationMode, TableMapping
from domain.value_objects.object_type import SystemRole


@pytest.fixture()
def landscape() -> SAPLandscape:
    return SAPLandscape(
        id="ls-test",
        programme_id="prog-1",
        system_id="DEV",
        system_role=SystemRole.DEV,
        db_size_gb=100.0,
        number_of_users=10,
        custom_object_count=0,
        integration_points=(),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture()
def pipeline_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def landscape_repo(landscape: SAPLandscape) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=landscape)
    return repo


@pytest.mark.asyncio
async def test_create_data_pipeline(
    pipeline_repo: MagicMock,
    landscape_repo: MagicMock,
    landscape: SAPLandscape,
) -> None:
    landscape_repo.get_by_id = AsyncMock(return_value=landscape)
    pipeline_repo.save = AsyncMock()
    uc = CreateDataPipelineUseCase(pipeline_repo, landscape_repo)
    req = CreateDataPipelineRequest(
        landscape_id=landscape.id,
        name="Test pipe",
        replication_mode=ReplicationMode.FULL,
        table_mappings=[
            TableMappingRequest(
                source_schema="S",
                source_table="T",
                target_dataset="d",
                target_table="t",
            )
        ],
    )
    resp = await uc.execute("prog-1", req)
    assert resp.programme_id == "prog-1"
    assert resp.landscape_id == landscape.id
    pipeline_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_pipeline_run_stub_happy_path(pipeline_repo: MagicMock, landscape: SAPLandscape) -> None:
    pipeline = DataPipeline(
        id="pipe-1",
        programme_id="prog-1",
        landscape_id=landscape.id,
        name="p",
        replication_mode=ReplicationMode.FULL,
        table_mappings=(
            TableMapping(
                source_schema="SAPHANADB",
                source_table="T1",
                target_dataset="ds1",
                target_table="t1",
            ),
        ),
        hana_connection_ref="default",
        created_at=datetime.now(timezone.utc),
    )
    pipeline_repo.get_by_id = AsyncMock(return_value=pipeline)

    run_repo = MagicMock()
    run_repo.save = AsyncMock()

    hana = MagicMock()
    hana.extract_table_to_csv = AsyncMock(return_value=(b"id,col\n1,x\n2,y\n", 5))

    staging = MagicMock()
    staging.stage_csv = AsyncMock(return_value="hanaforge-local://hana-bq/prog/run/t.csv")

    bq = MagicMock()
    bq.ensure_dataset_exists = AsyncMock()
    bq.load_csv_from_uri = AsyncMock(return_value="job-123")

    uc = StartPipelineRunUseCase(pipeline_repo, run_repo, hana, staging, bq)
    resp = await uc.execute(
        "prog-1",
        "pipe-1",
        connection_params={},
        request=StartPipelineRunRequest(row_limit_per_table=5),
    )
    assert resp.status.value == "completed"
    assert len(resp.table_results) == 1
    assert resp.table_results[0].rows_extracted == 5
    run_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_pipeline_run_rejects_cdc(pipeline_repo: MagicMock, landscape: SAPLandscape) -> None:
    pipeline = DataPipeline(
        id="pipe-cdc",
        programme_id="prog-1",
        landscape_id=landscape.id,
        name="p",
        replication_mode=ReplicationMode.CDC,
        table_mappings=(
            TableMapping(
                source_schema="S",
                source_table="T",
                target_dataset="d",
                target_table="t",
            ),
        ),
        hana_connection_ref="default",
        created_at=datetime.now(timezone.utc),
    )
    pipeline_repo.get_by_id = AsyncMock(return_value=pipeline)
    uc = StartPipelineRunUseCase(
        pipeline_repo,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    with pytest.raises(ValueError, match="CDC"):
        await uc.execute("prog-1", "pipe-cdc", {})
