"""Cutover Commander DTOs — Pydantic models for API serialisation."""

from __future__ import annotations

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class GenerateRunbookRequest(BaseModel):
    """Payload for generating a cutover runbook."""

    migration_tasks: list[dict] = []
    integration_inventory: list[dict] = []
    data_sequences: list[dict] = []


class StartHypercareRequest(BaseModel):
    """Payload for starting a hypercare session."""

    duration_days: int = 90
    monitoring_config: dict = {}


# ---------------------------------------------------------------------------
# Response models — Tasks & Gates
# ---------------------------------------------------------------------------


class CutoverTaskResponse(BaseModel):
    id: str
    name: str
    owner: str
    estimated_duration_minutes: int
    category: str
    gate_type: str | None = None
    rollback_action: str | None = None
    verification_step: str | None = None
    status: str = "NOT_STARTED"
    actual_duration_minutes: int | None = None


class GoNoGoGateResponse(BaseModel):
    id: str
    name: str
    gate_type: str
    status: str
    checks: list[dict] = []


# ---------------------------------------------------------------------------
# Response models — Runbook
# ---------------------------------------------------------------------------


class RunbookResponse(BaseModel):
    id: str
    programme_id: str
    version: int
    name: str
    task_count: int
    gate_count: int
    status: str
    approved_by: str | None = None
    created_at: str

    @staticmethod
    def from_entity(runbook) -> RunbookResponse:  # noqa: ANN001
        from domain.entities.cutover_runbook import CutoverRunbook

        rb: CutoverRunbook = runbook
        return RunbookResponse(
            id=rb.id,
            programme_id=rb.programme_id,
            version=rb.version,
            name=rb.name,
            task_count=len(rb.tasks),
            gate_count=len(rb.go_nogo_gates),
            status=rb.status.value,
            approved_by=rb.approved_by,
            created_at=rb.created_at.isoformat(),
        )


# ---------------------------------------------------------------------------
# Response models — Execution
# ---------------------------------------------------------------------------


class CutoverExecutionResponse(BaseModel):
    id: str
    runbook_id: str
    status: str
    started_at: str
    elapsed_minutes: int
    planned_duration_minutes: int
    tasks_completed: int
    tasks_remaining: int
    deviations_count: int
    issues_count: int

    @staticmethod
    def from_entity(execution) -> CutoverExecutionResponse:  # noqa: ANN001
        from domain.entities.cutover_execution import CutoverExecution

        ex: CutoverExecution = execution
        completed = sum(1 for t in ex.task_statuses if t.status == "COMPLETED")
        remaining = len(ex.task_statuses) - completed
        return CutoverExecutionResponse(
            id=ex.id,
            runbook_id=ex.runbook_id,
            status=ex.status.value,
            started_at=ex.started_at.isoformat(),
            elapsed_minutes=ex.elapsed_minutes,
            planned_duration_minutes=ex.planned_duration_minutes,
            tasks_completed=completed,
            tasks_remaining=remaining,
            deviations_count=len(ex.deviations),
            issues_count=len(ex.issues),
        )


# ---------------------------------------------------------------------------
# Response models — Status
# ---------------------------------------------------------------------------


class CutoverStatusResponse(BaseModel):
    programme_id: str
    runbook: RunbookResponse | None = None
    execution: CutoverExecutionResponse | None = None
    gates: list[GoNoGoGateResponse] = []
    critical_path_deviation_minutes: int = 0


class GateEvaluationResponse(BaseModel):
    gate_id: str
    gate_name: str
    status: str
    checks: list[dict] = []


# ---------------------------------------------------------------------------
# Response models — Hypercare
# ---------------------------------------------------------------------------


class HypercareIncidentResponse(BaseModel):
    id: str
    severity: str
    description: str
    sap_component: str | None = None
    reported_at: str
    resolved_at: str | None = None
    resolution: str | None = None
    ticket_id: str | None = None


class HypercareResponse(BaseModel):
    id: str
    programme_id: str
    status: str
    start_date: str
    end_date: str
    incidents_count: int
    knowledge_entries_count: int
    incidents: list[HypercareIncidentResponse] = []

    @staticmethod
    def from_entity(session) -> HypercareResponse:  # noqa: ANN001
        from domain.entities.hypercare_session import HypercareSession

        s: HypercareSession = session
        incident_responses = [
            HypercareIncidentResponse(
                id=inc.id,
                severity=inc.severity,
                description=inc.description,
                sap_component=inc.sap_component,
                reported_at=inc.reported_at.isoformat(),
                resolved_at=inc.resolved_at.isoformat() if inc.resolved_at else None,
                resolution=inc.resolution,
                ticket_id=inc.ticket_id,
            )
            for inc in s.incidents
        ]
        return HypercareResponse(
            id=s.id,
            programme_id=s.programme_id,
            status=s.status.value,
            start_date=s.start_date.isoformat(),
            end_date=s.end_date.isoformat(),
            incidents_count=len(s.incidents),
            knowledge_entries_count=len(s.knowledge_entries),
            incidents=incident_responses,
        )


# ---------------------------------------------------------------------------
# Response models — Lessons Learned
# ---------------------------------------------------------------------------


class LessonsLearnedResponse(BaseModel):
    programme_id: str
    entries: list[dict] = []
    total: int = 0
