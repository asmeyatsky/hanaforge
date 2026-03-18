"""Benchmark estimation service — pure domain logic for migration duration prediction.

Uses statistical methods (weighted mean, percentile-based confidence intervals)
to predict migration duration from historical benchmark data.  This is a pure
domain service with no infrastructure dependencies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from domain.entities.benchmark_entry import BenchmarkEntry
from domain.entities.programme import Programme
from domain.value_objects.benchmark_types import EstimationResult


@dataclass(frozen=True)
class _ScoredBenchmark:
    entry: BenchmarkEntry
    similarity: float


class BenchmarkEstimationService:
    """Estimates migration duration from comparable historical benchmarks."""

    # Weights for similarity scoring between a programme and a benchmark entry.
    _W_DB_SIZE = 0.30
    _W_OBJECT_COUNT = 0.25
    _W_VERSION_MATCH = 0.25
    _W_COMPLEXITY = 0.20

    # Minimum number of benchmarks required for a meaningful estimate.
    _MIN_SAMPLE_SIZE = 3

    def estimate_duration(
        self,
        programme: Programme,
        benchmarks: list[BenchmarkEntry],
        *,
        complexity_score: int | None = None,
        db_size_gb: float = 0.0,
        custom_object_count: int = 0,
    ) -> EstimationResult:
        """Produce a duration estimate with confidence intervals.

        Args:
            programme: The target migration programme.
            benchmarks: Historical benchmark entries to compare against.
            complexity_score: Optional complexity score (1-100) for the programme.
            db_size_gb: Database size in GB for the programme landscape.
            custom_object_count: Number of custom objects in the programme landscape.

        Returns:
            EstimationResult with predicted duration and confidence bounds.
        """
        if not benchmarks:
            return self._empty_estimate()

        # Score each benchmark for similarity to the target programme
        scored = [
            _ScoredBenchmark(
                entry=b,
                similarity=self._compute_similarity(
                    programme=programme,
                    entry=b,
                    complexity_score=complexity_score,
                    db_size_gb=db_size_gb,
                    custom_object_count=custom_object_count,
                ),
            )
            for b in benchmarks
        ]

        # Filter to entries with non-trivial similarity
        relevant = [s for s in scored if s.similarity > 0.1]
        if not relevant:
            relevant = scored  # Fall back to all entries if none are truly similar

        # Sort by similarity descending
        relevant.sort(key=lambda s: s.similarity, reverse=True)

        # Compute weighted mean duration
        total_weight = sum(s.similarity for s in relevant)
        if total_weight == 0:
            return self._empty_estimate()

        weighted_duration = sum(s.entry.duration_days * s.similarity for s in relevant) / total_weight

        # Compute confidence from sample size and similarity quality
        avg_similarity = total_weight / len(relevant)
        sample_factor = min(1.0, len(relevant) / 10)
        confidence = min(0.95, avg_similarity * sample_factor)

        # Percentile-based bounds from the relevant set
        durations = sorted(s.entry.duration_days for s in relevant)
        p25 = self._percentile(durations, 25)
        p75 = self._percentile(durations, 75)

        # Risk factors
        risk_factors = self._identify_risk_factors(
            programme=programme,
            benchmarks=[s.entry for s in relevant],
            db_size_gb=db_size_gb,
            custom_object_count=custom_object_count,
        )

        # Widen bounds if confidence is low
        spread_factor = 1.0 + (1.0 - confidence) * 0.5
        lower = max(1.0, min(p25, weighted_duration * (1.0 / spread_factor)))
        upper = max(p75, weighted_duration * spread_factor)

        return EstimationResult(
            estimated_duration_days=round(weighted_duration, 1),
            confidence_level=round(confidence, 3),
            lower_bound_days=round(lower, 1),
            upper_bound_days=round(upper, 1),
            sample_size=len(relevant),
            comparable_projects=sum(1 for s in relevant if s.similarity >= 0.5),
            risk_factors=tuple(risk_factors),
        )

    # ------------------------------------------------------------------
    # Similarity computation
    # ------------------------------------------------------------------

    def _compute_similarity(
        self,
        programme: Programme,
        entry: BenchmarkEntry,
        *,
        complexity_score: int | None,
        db_size_gb: float,
        custom_object_count: int,
    ) -> float:
        version_sim = self._version_similarity(
            programme.sap_source_version,
            programme.target_version,
            entry.source_version,
            entry.target_version,
        )
        db_sim = self._numeric_similarity(db_size_gb, entry.db_size_gb)
        obj_sim = self._numeric_similarity(float(custom_object_count), float(entry.custom_object_count))

        prog_complexity = complexity_score if complexity_score is not None else 50
        complexity_sim = self._numeric_similarity(float(prog_complexity), float(entry.complexity_score))

        return (
            version_sim * self._W_VERSION_MATCH
            + db_sim * self._W_DB_SIZE
            + obj_sim * self._W_OBJECT_COUNT
            + complexity_sim * self._W_COMPLEXITY
        )

    @staticmethod
    def _version_similarity(src_a: str, tgt_a: str, src_b: str, tgt_b: str) -> float:
        score = 0.0
        if src_a == src_b:
            score += 0.5
        if tgt_a == tgt_b:
            score += 0.5
        return score

    @staticmethod
    def _numeric_similarity(a: float, b: float) -> float:
        if a == 0 and b == 0:
            return 1.0
        max_val = max(abs(a), abs(b))
        if max_val == 0:
            return 1.0
        return 1.0 - min(1.0, abs(a - b) / max_val)

    # ------------------------------------------------------------------
    # Statistical helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _percentile(sorted_values: list[int], pct: int) -> float:
        if not sorted_values:
            return 0.0
        n = len(sorted_values)
        k = (pct / 100) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_values[int(k)])
        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)

    # ------------------------------------------------------------------
    # Risk factor identification
    # ------------------------------------------------------------------

    @staticmethod
    def _identify_risk_factors(
        programme: Programme,
        benchmarks: list[BenchmarkEntry],
        db_size_gb: float,
        custom_object_count: int,
    ) -> list[str]:
        risks: list[str] = []

        # Check failure rate in comparable set
        if benchmarks:
            failure_rate = sum(1 for b in benchmarks if not b.success) / len(benchmarks)
            if failure_rate > 0.3:
                risks.append(f"High failure rate ({failure_rate:.0%}) in comparable migrations")

        # Large database
        if db_size_gb > 5000:
            risks.append(f"Large database ({db_size_gb:.0f} GB) increases migration window")

        # High custom object count
        if custom_object_count > 3000:
            risks.append(f"High custom object count ({custom_object_count}) requires extensive testing")

        # Version jump
        if programme.sap_source_version and programme.target_version:
            if programme.sap_source_version.startswith("ECC") or programme.sap_source_version.startswith("4."):
                risks.append("Major version jump (ECC to S/4HANA) adds complexity")

        return risks

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_estimate() -> EstimationResult:
        return EstimationResult(
            estimated_duration_days=0.0,
            confidence_level=0.0,
            lower_bound_days=0.0,
            upper_bound_days=0.0,
            sample_size=0,
            comparable_projects=0,
            risk_factors=("Insufficient benchmark data for estimation",),
        )
