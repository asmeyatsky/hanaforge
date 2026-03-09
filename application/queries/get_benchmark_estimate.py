"""GetBenchmarkEstimateQuery — retrieves benchmark-based duration estimate for a programme."""

from __future__ import annotations

from pydantic import BaseModel

from domain.ports.benchmark_ports import BenchmarkRepositoryPort
from domain.ports.repository_ports import LandscapeRepositoryPort, ProgrammeRepositoryPort
from domain.services.benchmark_estimation_service import BenchmarkEstimationService
from domain.value_objects.benchmark_types import BenchmarkCriteria


class BenchmarkEstimateResponse(BaseModel):
    """API-serialisable benchmark estimation result."""

    programme_id: str
    estimated_duration_days: float
    confidence_level: float
    lower_bound_days: float
    upper_bound_days: float
    sample_size: int
    comparable_projects: int
    risk_factors: list[str]


class GetBenchmarkEstimateQuery:
    """Read-only query: produce a duration estimate from historical benchmarks."""

    def __init__(
        self,
        programme_repo: ProgrammeRepositoryPort,
        landscape_repo: LandscapeRepositoryPort,
        benchmark_repo: BenchmarkRepositoryPort,
        estimation_service: BenchmarkEstimationService,
    ) -> None:
        self._programme_repo = programme_repo
        self._landscape_repo = landscape_repo
        self._benchmark_repo = benchmark_repo
        self._estimation_service = estimation_service

    async def execute(self, programme_id: str) -> BenchmarkEstimateResponse:
        # 1. Load programme
        programme = await self._programme_repo.get_by_id(programme_id)
        if programme is None:
            raise ValueError(f"Programme {programme_id} not found")

        # 2. Load landscape data for sizing context
        landscapes = await self._landscape_repo.list_by_programme(programme_id)
        db_size_gb = 0.0
        custom_object_count = 0
        if landscapes:
            # Use the latest landscape snapshot
            latest = max(landscapes, key=lambda l: l.created_at)
            db_size_gb = latest.db_size_gb
            custom_object_count = latest.custom_object_count

        # 3. Find similar benchmarks using programme attributes
        criteria = BenchmarkCriteria(
            source_version=programme.sap_source_version,
            target_version=programme.target_version,
        )
        benchmarks = await self._benchmark_repo.find_similar(criteria, limit=20)

        # 4. If no version-matched results, fall back to all benchmarks
        if not benchmarks:
            benchmarks = await self._benchmark_repo.list_all()

        # 5. Compute estimation
        complexity_score = (
            programme.complexity_score.score if programme.complexity_score else None
        )
        estimation = self._estimation_service.estimate_duration(
            programme=programme,
            benchmarks=benchmarks,
            complexity_score=complexity_score,
            db_size_gb=db_size_gb,
            custom_object_count=custom_object_count,
        )

        return BenchmarkEstimateResponse(
            programme_id=programme_id,
            estimated_duration_days=estimation.estimated_duration_days,
            confidence_level=estimation.confidence_level,
            lower_bound_days=estimation.lower_bound_days,
            upper_bound_days=estimation.upper_bound_days,
            sample_size=estimation.sample_size,
            comparable_projects=estimation.comparable_projects,
            risk_factors=list(estimation.risk_factors),
        )
