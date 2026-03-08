"""Programme DTOs — Pydantic models for API serialization."""

from __future__ import annotations

from pydantic import BaseModel

from domain.entities.programme import Programme


class CreateProgrammeRequest(BaseModel):
    """Request payload to create a new migration programme."""

    name: str
    customer_id: str
    sap_source_version: str
    target_version: str
    go_live_date: str | None = None


class ProgrammeResponse(BaseModel):
    """Serialisable representation of a Programme entity."""

    id: str
    name: str
    customer_id: str
    sap_source_version: str
    target_version: str
    status: str
    complexity_score: dict | None = None
    created_at: str

    @staticmethod
    def from_entity(programme: Programme) -> ProgrammeResponse:
        complexity: dict | None = None
        if programme.complexity_score is not None:
            complexity = {
                "score": programme.complexity_score.score,
                "risk_level": programme.complexity_score.risk_level,
                "benchmark_percentile": programme.complexity_score.benchmark_percentile,
            }

        return ProgrammeResponse(
            id=programme.id,
            name=programme.name,
            customer_id=programme.customer_id,
            sap_source_version=programme.sap_source_version,
            target_version=programme.target_version,
            status=programme.status.value,
            complexity_score=complexity,
            created_at=programme.created_at.isoformat(),
        )


class ProgrammeListResponse(BaseModel):
    """Paginated list of programmes."""

    programmes: list[ProgrammeResponse]
    total: int
