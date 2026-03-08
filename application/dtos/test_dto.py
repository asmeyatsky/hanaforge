"""TestForge DTOs — Pydantic models for API serialization of test scenarios."""

from __future__ import annotations

from pydantic import BaseModel


class TestStepResponse(BaseModel):
    """Serialisable representation of a single test step."""

    step_number: int
    action: str
    expected_result: str
    sap_transaction: str | None = None
    test_data: str | None = None


class TestScenarioResponse(BaseModel):
    """Serialisable representation of a TestScenario entity."""

    id: str
    scenario_name: str
    process_area: str
    description: str
    steps_count: int
    priority: str
    status: str
    sap_transaction: str | None = None
    fiori_app_id: str | None = None
    tags: list[str] = []


class TestGenerationResponse(BaseModel):
    """Response returned after test generation completes."""

    programme_id: str
    total_generated: int
    by_process_area: dict[str, int]
    scenarios: list[TestScenarioResponse]


class TestResultsResponse(BaseModel):
    """Response for test result summaries."""

    programme_id: str
    total_scenarios: int
    by_status: dict[str, int]
    by_process_area: dict[str, int]
    coverage_percentage: float
    scenarios: list[TestScenarioResponse]


class TraceabilityMatrixResponse(BaseModel):
    """Response for the traceability matrix."""

    programme_id: str
    entries: list[dict]
    coverage_percentage: float
    untested_processes: list[str]


class ExportRequest(BaseModel):
    """Request payload for test export."""

    format: str
    process_area: str | None = None
