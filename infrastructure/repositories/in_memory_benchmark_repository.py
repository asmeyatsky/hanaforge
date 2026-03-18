"""InMemoryBenchmarkRepository — dev-mode in-memory implementation with seed data.

Pre-loaded with ~20 realistic SAP migration benchmark entries spanning
various industries, system sizes, and migration paths.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from domain.entities.benchmark_entry import BenchmarkEntry
from domain.value_objects.benchmark_types import BenchmarkCriteria, BenchmarkStatistics


def _seed_benchmarks() -> list[BenchmarkEntry]:
    """Generate ~20 realistic SAP migration benchmark entries."""
    return [
        BenchmarkEntry(
            id="bench-001",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2021",
            db_size_gb=450.0,
            custom_object_count=1200,
            duration_days=180,
            team_size=15,
            complexity_score=55,
            industry="Manufacturing",
            region="Europe",
            success=True,
            lessons_learned=(
                "Early custom code remediation reduced go-live risk",
                "Parallel testing tracks saved 3 weeks",
            ),
            created_at=datetime(2023, 6, 15, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-002",
            source_version="ECC 6.0 EHP7",
            target_version="S/4HANA 2020",
            db_size_gb=1200.0,
            custom_object_count=3500,
            duration_days=365,
            team_size=30,
            complexity_score=78,
            industry="Automotive",
            region="Europe",
            success=True,
            lessons_learned=(
                "Data archiving before migration reduced downtime by 40%",
                "Dedicated Fiori UX workstream was essential",
            ),
            created_at=datetime(2022, 11, 1, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-003",
            source_version="ECC 6.0 EHP6",
            target_version="S/4HANA 2021",
            db_size_gb=200.0,
            custom_object_count=400,
            duration_days=90,
            team_size=8,
            complexity_score=30,
            industry="Retail",
            region="North America",
            success=True,
            lessons_learned=(
                "Small custom footprint enabled accelerated greenfield approach",
                "Business process re-engineering drove adoption",
            ),
            created_at=datetime(2023, 3, 20, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-004",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2022",
            db_size_gb=2500.0,
            custom_object_count=5200,
            duration_days=480,
            team_size=45,
            complexity_score=88,
            industry="Oil & Gas",
            region="Middle East",
            success=True,
            lessons_learned=(
                "Phased rollout across plants minimized business disruption",
                "SAP RISE managed services reduced infrastructure complexity",
            ),
            created_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-005",
            source_version="ECC 6.0 EHP5",
            target_version="S/4HANA 2020",
            db_size_gb=800.0,
            custom_object_count=2800,
            duration_days=300,
            team_size=22,
            complexity_score=68,
            industry="Pharmaceuticals",
            region="North America",
            success=False,
            lessons_learned=(
                "Insufficient testing of GxP-validated processes caused delays",
                "Underestimated data migration complexity for batch records",
                "Project restarted with revised scope after 8 months",
            ),
            created_at=datetime(2022, 8, 5, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-006",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
            db_size_gb=350.0,
            custom_object_count=900,
            duration_days=150,
            team_size=12,
            complexity_score=45,
            industry="Consumer Products",
            region="Europe",
            success=True,
            lessons_learned=(
                "Brownfield conversion preserved existing customizations effectively",
                "Automated regression testing with CBTA saved significant effort",
            ),
            created_at=datetime(2024, 5, 22, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-007",
            source_version="S/4HANA 1909",
            target_version="S/4HANA 2023",
            db_size_gb=600.0,
            custom_object_count=1500,
            duration_days=120,
            team_size=10,
            complexity_score=35,
            industry="Utilities",
            region="North America",
            success=True,
            lessons_learned=(
                "S/4 to S/4 upgrade was significantly simpler than ECC conversion",
                "IS-U specific objects required specialist knowledge",
            ),
            created_at=datetime(2024, 9, 1, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-008",
            source_version="ECC 6.0 EHP7",
            target_version="S/4HANA 2022",
            db_size_gb=3200.0,
            custom_object_count=4100,
            duration_days=420,
            team_size=35,
            complexity_score=82,
            industry="Banking",
            region="Asia Pacific",
            success=True,
            lessons_learned=(
                "Regulatory compliance requirements added 60 days to timeline",
                "Dual maintenance period required dedicated team",
            ),
            created_at=datetime(2024, 3, 15, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-009",
            source_version="ECC 6.0 EHP6",
            target_version="S/4HANA 2021",
            db_size_gb=150.0,
            custom_object_count=250,
            duration_days=75,
            team_size=6,
            complexity_score=22,
            industry="Professional Services",
            region="Europe",
            success=True,
            lessons_learned=(
                "Lean custom footprint enabled rapid greenfield deployment",
                "Change management was the primary challenge, not technical",
            ),
            created_at=datetime(2023, 7, 10, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-010",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
            db_size_gb=1800.0,
            custom_object_count=3200,
            duration_days=330,
            team_size=28,
            complexity_score=72,
            industry="Manufacturing",
            region="Asia Pacific",
            success=True,
            lessons_learned=(
                "Multi-plant rollout required careful sequence planning",
                "MES integration points needed complete rearchitecture",
            ),
            created_at=datetime(2025, 1, 5, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-011",
            source_version="ECC 6.0 EHP7",
            target_version="S/4HANA 2021",
            db_size_gb=950.0,
            custom_object_count=2100,
            duration_days=270,
            team_size=20,
            complexity_score=62,
            industry="Chemicals",
            region="Europe",
            success=True,
            lessons_learned=(
                "EHS compliance objects required extensive rework for S/4",
                "Batch management simplification items were most impactful",
            ),
            created_at=datetime(2023, 12, 1, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-012",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2022",
            db_size_gb=500.0,
            custom_object_count=1800,
            duration_days=210,
            team_size=18,
            complexity_score=58,
            industry="Retail",
            region="North America",
            success=False,
            lessons_learned=(
                "POS integration failures during cutover forced rollback",
                "Insufficient performance testing for peak-season loads",
                "Second attempt succeeded 4 months later with revised cutover plan",
            ),
            created_at=datetime(2023, 10, 20, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-013",
            source_version="ECC 6.0 EHP6",
            target_version="S/4HANA 2023",
            db_size_gb=700.0,
            custom_object_count=1600,
            duration_days=240,
            team_size=16,
            complexity_score=52,
            industry="Aerospace & Defense",
            region="North America",
            success=True,
            lessons_learned=(
                "ITAR compliance controls required dedicated security workstream",
                "MRP Live migration required extensive parallel run validation",
            ),
            created_at=datetime(2025, 2, 28, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-014",
            source_version="S/4HANA 1809",
            target_version="S/4HANA 2022",
            db_size_gb=400.0,
            custom_object_count=800,
            duration_days=100,
            team_size=8,
            complexity_score=28,
            industry="Healthcare",
            region="Europe",
            success=True,
            lessons_learned=(
                "In-place upgrade from older S/4 was straightforward",
                "Patient data migration required GDPR compliance review",
            ),
            created_at=datetime(2024, 7, 12, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-015",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
            db_size_gb=5500.0,
            custom_object_count=7200,
            duration_days=540,
            team_size=60,
            complexity_score=95,
            industry="Mining",
            region="South America",
            success=True,
            lessons_learned=(
                "Largest single-instance migration required 18-month program",
                "Near-zero downtime achieved with SAP DMLT optimizations",
                "Remote site connectivity was a persistent challenge",
            ),
            created_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-016",
            source_version="ECC 6.0 EHP7",
            target_version="S/4HANA 2022",
            db_size_gb=300.0,
            custom_object_count=600,
            duration_days=130,
            team_size=10,
            complexity_score=38,
            industry="Telecommunications",
            region="Asia Pacific",
            success=True,
            lessons_learned=(
                "Revenue recognition changes under IFRS 15 drove scope expansion",
                "API-first approach for integrations simplified cutover",
            ),
            created_at=datetime(2024, 4, 18, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-017",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2021",
            db_size_gb=1100.0,
            custom_object_count=2600,
            duration_days=280,
            team_size=24,
            complexity_score=65,
            industry="Automotive",
            region="North America",
            success=False,
            lessons_learned=(
                "EDI interface failures with tier-1 suppliers caused production stops",
                "Project paused for 3 months to redesign integration architecture",
                "Completed successfully after scope and timeline reset",
            ),
            created_at=datetime(2023, 9, 8, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-018",
            source_version="ECC 6.0 EHP8",
            target_version="S/4HANA 2023",
            db_size_gb=750.0,
            custom_object_count=1400,
            duration_days=200,
            team_size=14,
            complexity_score=50,
            industry="Consumer Products",
            region="North America",
            success=True,
            lessons_learned=(
                "Trade promotion management required complete redesign for S/4",
                "Embedded analytics reduced need for BW extractors",
            ),
            created_at=datetime(2025, 1, 20, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-019",
            source_version="ECC 6.0 EHP6",
            target_version="S/4HANA 2022",
            db_size_gb=180.0,
            custom_object_count=350,
            duration_days=85,
            team_size=7,
            complexity_score=25,
            industry="Education",
            region="Europe",
            success=True,
            lessons_learned=(
                "Public sector procurement rules required custom workflow redesign",
                "Greenfield approach chosen due to small custom footprint",
            ),
            created_at=datetime(2024, 6, 30, tzinfo=timezone.utc),
        ),
        BenchmarkEntry(
            id="bench-020",
            source_version="ECC 6.0 EHP7",
            target_version="S/4HANA 2023",
            db_size_gb=2200.0,
            custom_object_count=3800,
            duration_days=390,
            team_size=32,
            complexity_score=75,
            industry="Logistics",
            region="Europe",
            success=True,
            lessons_learned=(
                "Warehouse management migration to EWM was the critical path",
                "Transportation management required complete reimplementation",
                "RISE with SAP hosting simplified infrastructure provisioning",
            ),
            created_at=datetime(2025, 2, 14, tzinfo=timezone.utc),
        ),
    ]


class InMemoryBenchmarkRepository:
    """Implements BenchmarkRepositoryPort using a plain Python dict with seed data."""

    def __init__(self) -> None:
        self._store: dict[str, BenchmarkEntry] = {}
        for entry in _seed_benchmarks():
            self._store[entry.id] = entry

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, entry: BenchmarkEntry) -> None:
        self._store[entry.id] = entry

    async def get_by_id(self, id: str) -> BenchmarkEntry | None:
        return self._store.get(id)

    async def list_all(self) -> list[BenchmarkEntry]:
        return list(self._store.values())

    async def find_similar(self, criteria: BenchmarkCriteria, limit: int = 10) -> list[BenchmarkEntry]:
        results = [entry for entry in self._store.values() if self._matches_criteria(entry, criteria)]
        # Sort by recency (newest first)
        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[:limit]

    async def get_statistics(self, criteria: BenchmarkCriteria) -> BenchmarkStatistics:
        entries = [entry for entry in self._store.values() if self._matches_criteria(entry, criteria)]

        if not entries:
            return BenchmarkStatistics(
                total_count=0,
                avg_duration_days=0.0,
                median_duration_days=0.0,
                avg_team_size=0.0,
                success_rate=0.0,
                p25_duration=0.0,
                p75_duration=0.0,
            )

        durations = sorted(e.duration_days for e in entries)
        team_sizes = [e.team_size for e in entries]
        success_count = sum(1 for e in entries if e.success)
        n = len(entries)

        return BenchmarkStatistics(
            total_count=n,
            avg_duration_days=round(sum(durations) / n, 1),
            median_duration_days=self._median(durations),
            avg_team_size=round(sum(team_sizes) / n, 1),
            success_rate=round(success_count / n, 3),
            p25_duration=self._percentile(durations, 25),
            p75_duration=self._percentile(durations, 75),
        )

    # ------------------------------------------------------------------
    # Filtering logic
    # ------------------------------------------------------------------

    @staticmethod
    def _matches_criteria(entry: BenchmarkEntry, criteria: BenchmarkCriteria) -> bool:
        if criteria.source_version is not None:
            if criteria.source_version.lower() not in entry.source_version.lower():
                return False

        if criteria.target_version is not None:
            if criteria.target_version.lower() not in entry.target_version.lower():
                return False

        if criteria.db_size_range is not None:
            lo, hi = criteria.db_size_range
            if not (lo <= entry.db_size_gb <= hi):
                return False

        if criteria.object_count_range is not None:
            lo, hi = criteria.object_count_range
            if not (lo <= entry.custom_object_count <= hi):
                return False

        if criteria.industry is not None:
            if criteria.industry.lower() not in entry.industry.lower():
                return False

        return True

    # ------------------------------------------------------------------
    # Statistical helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _median(sorted_values: list[int]) -> float:
        n = len(sorted_values)
        if n == 0:
            return 0.0
        mid = n // 2
        if n % 2 == 0:
            return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0
        return float(sorted_values[mid])

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
        return round(sorted_values[f] * (c - k) + sorted_values[c] * (k - f), 1)
