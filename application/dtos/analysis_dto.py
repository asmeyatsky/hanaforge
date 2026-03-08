"""Analysis DTOs — Pydantic models for ABAP analysis and discovery results."""

from __future__ import annotations

from pydantic import BaseModel


class UploadABAPRequest(BaseModel):
    """Request payload identifying the target landscape for an ABAP upload."""

    landscape_id: str


class ABAPAnalysisResponse(BaseModel):
    """Analysis result for a single custom ABAP object."""

    object_id: str
    object_name: str
    object_type: str
    compatibility_status: str
    deprecated_apis: list[str]
    effort_points: int | None = None
    remediation_available: bool = False


class AnalysisResultsResponse(BaseModel):
    """Aggregate analysis results for a programme landscape."""

    programme_id: str
    total_objects: int
    compatible_count: int
    incompatible_count: int
    needs_review_count: int
    objects: list[ABAPAnalysisResponse]


class DiscoveryResultsResponse(BaseModel):
    """Results from an SAP landscape discovery run."""

    programme_id: str
    landscape_id: str
    system_id: str
    custom_object_count: int
    integration_point_count: int
    complexity_score: dict | None = None
    migration_recommendation: dict | None = None
