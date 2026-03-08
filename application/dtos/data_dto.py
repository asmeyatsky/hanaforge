"""Data readiness DTOs — Pydantic models for data profiling and assessment results."""

from __future__ import annotations

from pydantic import BaseModel


class DataDomainResponse(BaseModel):
    """Serialisable representation of a DataDomain entity."""

    id: str
    table_name: str
    record_count: int
    field_count: int
    quality_score: dict | None = None
    migration_status: str
    null_rate_summary: float | None = None
    duplicate_key_count: int = 0


class DataProfilingResultsResponse(BaseModel):
    """Aggregate profiling results for a landscape."""

    landscape_id: str
    total_tables: int
    tables_profiled: int
    overall_quality: float
    risk_level: str
    domains: list[DataDomainResponse]
    risk_register: list[dict]


class BPConsolidationResponse(BaseModel):
    """Business Partner consolidation assessment result."""

    customer_count: int
    vendor_count: int
    duplicate_pairs: int
    merge_candidates_count: int
    consolidation_complexity: str


class UniversalJournalResponse(BaseModel):
    """Universal Journal migration assessment result."""

    custom_coding_blocks: list[str]
    profit_centre_assignments: int
    segment_reporting_configs: int
    fi_gl_simplification_impact: str
    migration_complexity: str
