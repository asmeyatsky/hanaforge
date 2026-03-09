"""Benchmark routes — migration benchmarking and duration estimation endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from application.queries.get_benchmark_estimate import (
    BenchmarkEstimateResponse,
    GetBenchmarkEstimateQuery,
)
from domain.entities.benchmark_entry import BenchmarkEntry
from domain.ports.benchmark_ports import BenchmarkRepositoryPort
from domain.value_objects.benchmark_types import BenchmarkCriteria
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["Migration Benchmarks"])


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------


class BenchmarkEntryResponse(BaseModel):
    """Serialised benchmark entry."""

    id: str
    source_version: str
    target_version: str
    db_size_gb: float
    custom_object_count: int
    duration_days: int
    team_size: int
    complexity_score: int
    industry: str
    region: str
    success: bool
    lessons_learned: list[str]
    created_at: str


class BenchmarkListResponse(BaseModel):
    """List of similar benchmark entries."""

    benchmarks: list[BenchmarkEntryResponse]
    total: int


class BenchmarkStatisticsResponse(BaseModel):
    """Aggregate benchmark statistics."""

    total_count: int
    avg_duration_days: float
    median_duration_days: float
    avg_team_size: float
    success_rate: float
    p25_duration: float
    p75_duration: float


class CreateBenchmarkRequest(BaseModel):
    """Payload to submit a new benchmark entry."""

    source_version: str
    target_version: str
    db_size_gb: float
    custom_object_count: int
    duration_days: int
    team_size: int
    complexity_score: int
    industry: str
    region: str
    success: bool
    lessons_learned: list[str] = []


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get(
    "/estimate/{programme_id}",
    response_model=BenchmarkEstimateResponse,
    summary="Get duration estimate for a programme",
)
async def get_benchmark_estimate(
    programme_id: str,
    request: Request,
    _user=Depends(get_current_user),
) -> BenchmarkEstimateResponse:
    """Produce a benchmark-based migration duration estimate for a programme.

    Uses historical benchmark data and statistical methods to predict
    duration with confidence intervals.
    """
    container = request.app.state.container
    query: GetBenchmarkEstimateQuery = container.resolve(GetBenchmarkEstimateQuery)

    try:
        return await query.execute(programme_id=programme_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/similar",
    response_model=BenchmarkListResponse,
    summary="Find similar past migrations",
)
async def find_similar(
    request: Request,
    source_version: str | None = Query(None, description="Filter by source SAP version"),
    target_version: str | None = Query(None, description="Filter by target SAP version"),
    db_size_min: float | None = Query(None, description="Minimum database size in GB"),
    db_size_max: float | None = Query(None, description="Maximum database size in GB"),
    object_count_min: int | None = Query(None, description="Minimum custom object count"),
    object_count_max: int | None = Query(None, description="Maximum custom object count"),
    industry: str | None = Query(None, description="Filter by industry"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    _user=Depends(get_current_user),
) -> BenchmarkListResponse:
    """Find historically similar SAP migrations matching the given criteria."""
    container = request.app.state.container
    repo: BenchmarkRepositoryPort = container.resolve(BenchmarkRepositoryPort)

    db_size_range = None
    if db_size_min is not None or db_size_max is not None:
        db_size_range = (db_size_min or 0.0, db_size_max or 999999.0)

    object_count_range = None
    if object_count_min is not None or object_count_max is not None:
        object_count_range = (object_count_min or 0, object_count_max or 999999)

    criteria = BenchmarkCriteria(
        source_version=source_version,
        target_version=target_version,
        db_size_range=db_size_range,
        object_count_range=object_count_range,
        industry=industry,
    )

    entries = await repo.find_similar(criteria, limit=limit)

    return BenchmarkListResponse(
        benchmarks=[
            BenchmarkEntryResponse(
                id=e.id,
                source_version=e.source_version,
                target_version=e.target_version,
                db_size_gb=e.db_size_gb,
                custom_object_count=e.custom_object_count,
                duration_days=e.duration_days,
                team_size=e.team_size,
                complexity_score=e.complexity_score,
                industry=e.industry,
                region=e.region,
                success=e.success,
                lessons_learned=list(e.lessons_learned),
                created_at=e.created_at.isoformat(),
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.get(
    "/statistics",
    response_model=BenchmarkStatisticsResponse,
    summary="Get aggregate benchmark statistics",
)
async def get_statistics(
    request: Request,
    source_version: str | None = Query(None, description="Filter by source SAP version"),
    target_version: str | None = Query(None, description="Filter by target SAP version"),
    industry: str | None = Query(None, description="Filter by industry"),
    _user=Depends(get_current_user),
) -> BenchmarkStatisticsResponse:
    """Compute aggregate statistics from the benchmark database."""
    container = request.app.state.container
    repo: BenchmarkRepositoryPort = container.resolve(BenchmarkRepositoryPort)

    criteria = BenchmarkCriteria(
        source_version=source_version,
        target_version=target_version,
        industry=industry,
    )

    stats = await repo.get_statistics(criteria)

    return BenchmarkStatisticsResponse(
        total_count=stats.total_count,
        avg_duration_days=stats.avg_duration_days,
        median_duration_days=stats.median_duration_days,
        avg_team_size=stats.avg_team_size,
        success_rate=stats.success_rate,
        p25_duration=stats.p25_duration,
        p75_duration=stats.p75_duration,
    )


@router.post(
    "/",
    response_model=BenchmarkEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new benchmark entry",
)
async def create_benchmark(
    body: CreateBenchmarkRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> BenchmarkEntryResponse:
    """Submit a new migration benchmark entry to the database."""
    container = request.app.state.container
    repo: BenchmarkRepositoryPort = container.resolve(BenchmarkRepositoryPort)

    import uuid

    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    try:
        entry = BenchmarkEntry(
            id=entry_id,
            source_version=body.source_version,
            target_version=body.target_version,
            db_size_gb=body.db_size_gb,
            custom_object_count=body.custom_object_count,
            duration_days=body.duration_days,
            team_size=body.team_size,
            complexity_score=body.complexity_score,
            industry=body.industry,
            region=body.region,
            success=body.success,
            lessons_learned=tuple(body.lessons_learned),
            created_at=now,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await repo.save(entry)

    return BenchmarkEntryResponse(
        id=entry.id,
        source_version=entry.source_version,
        target_version=entry.target_version,
        db_size_gb=entry.db_size_gb,
        custom_object_count=entry.custom_object_count,
        duration_days=entry.duration_days,
        team_size=entry.team_size,
        complexity_score=entry.complexity_score,
        industry=entry.industry,
        region=entry.region,
        success=entry.success,
        lessons_learned=list(entry.lessons_learned),
        created_at=entry.created_at.isoformat(),
    )
