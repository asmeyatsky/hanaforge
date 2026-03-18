"""Cutover Commander value objects — frozen dataclasses and enums for cutover domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GateType(Enum):
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    DATA_RECONCILIATION = "DATA_RECONCILIATION"
    INTERFACE_CONNECTIVITY = "INTERFACE_CONNECTIVITY"
    PERFORMANCE_BASELINE = "PERFORMANCE_BASELINE"
    BUSINESS_SIGN_OFF = "BUSINESS_SIGN_OFF"
    FINAL_GO_LIVE = "FINAL_GO_LIVE"


class GateStatus(Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    PASSED = "PASSED"
    FAILED = "FAILED"
    OVERRIDDEN = "OVERRIDDEN"


class CutoverCategory(Enum):
    PREPARATION = "PREPARATION"
    SYSTEM_LOCKDOWN = "SYSTEM_LOCKDOWN"
    DATA_MIGRATION = "DATA_MIGRATION"
    TECHNICAL_CUTOVER = "TECHNICAL_CUTOVER"
    VALIDATION = "VALIDATION"
    COMMUNICATION = "COMMUNICATION"
    GO_LIVE = "GO_LIVE"
    POST_GO_LIVE = "POST_GO_LIVE"


class RunbookStatus(Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    IN_EXECUTION = "IN_EXECUTION"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class ExecutionStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    ROLLED_BACK = "ROLLED_BACK"


class HypercareStatus(Enum):
    ACTIVE = "ACTIVE"
    MONITORING = "MONITORING"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class ApprovalStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class StepCategory(Enum):
    PREPARATION = "PREPARATION"
    SYSTEM_LOCKDOWN = "SYSTEM_LOCKDOWN"
    DATA_MIGRATION = "DATA_MIGRATION"
    TECHNICAL_CUTOVER = "TECHNICAL_CUTOVER"
    VALIDATION = "VALIDATION"
    COMMUNICATION = "COMMUNICATION"
    GO_LIVE = "GO_LIVE"
    POST_GO_LIVE = "POST_GO_LIVE"


class TaskProgressStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class IncidentSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthCheck:
    """Single health-check assertion within a go/no-go gate."""

    name: str
    check_type: str
    target_value: str
    actual_value: str | None = None
    passed: bool | None = None


@dataclass(frozen=True)
class CutoverTask:
    """An individual task inside a cutover runbook."""

    id: str
    name: str
    owner: str
    estimated_duration_minutes: int
    depends_on: tuple[str, ...] = ()
    gate_type: GateType | None = None
    rollback_action: str | None = None
    verification_step: str | None = None
    category: CutoverCategory = CutoverCategory.PREPARATION
    order: int = 0


@dataclass(frozen=True)
class GoNoGoGate:
    """A decision gate requiring health checks before proceeding."""

    id: str
    name: str
    gate_type: GateType
    checks: tuple[HealthCheck, ...] = ()
    required_approval: bool = True
    status: GateStatus = GateStatus.NOT_EVALUATED


@dataclass(frozen=True)
class TaskExecution:
    """Runtime status tracking for an individual cutover task."""

    task_id: str
    task_name: str
    status: str = "NOT_STARTED"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    actual_duration_minutes: int | None = None
    notes: str | None = None
    executor: str | None = None


@dataclass(frozen=True)
class ExecutionDeviation:
    """Records any deviation from the planned runbook during execution."""

    task_id: str
    deviation_type: str  # DELAY | SKIP | REORDER | FAILURE | MANUAL_OVERRIDE
    planned_value: str
    actual_value: str
    impact: str
    recorded_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.recorded_at is None:
            from datetime import timezone

            object.__setattr__(self, "recorded_at", datetime.now(timezone.utc))


@dataclass(frozen=True)
class CutoverIssue:
    """An issue raised during cutover execution."""

    id: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    description: str
    affected_task_id: str | None = None
    resolution: str | None = None
    raised_at: datetime = None  # type: ignore[assignment]
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.raised_at is None:
            from datetime import timezone

            object.__setattr__(self, "raised_at", datetime.now(timezone.utc))


@dataclass(frozen=True)
class RollbackPlan:
    """Defines the rollback strategy for a cutover runbook."""

    trigger_conditions: tuple[str, ...] = ()
    rollback_steps: tuple[str, ...] = ()
    max_rollback_window_hours: int = 4
    point_of_no_return_task_id: str | None = None


@dataclass(frozen=True)
class MonitoringConfig:
    """Configuration for hypercare monitoring."""

    alert_channels: tuple[str, ...] = ()
    check_interval_minutes: int = 15
    escalation_contacts: tuple[str, ...] = ()
    sla_response_minutes: int = 30


@dataclass(frozen=True)
class HypercareIncident:
    """An incident recorded during the hypercare period."""

    id: str
    severity: str
    description: str
    sap_component: str | None = None
    reported_at: datetime = None  # type: ignore[assignment]
    resolved_at: datetime | None = None
    resolution: str | None = None
    ticket_id: str | None = None

    def __post_init__(self) -> None:
        if self.reported_at is None:
            from datetime import timezone

            object.__setattr__(self, "reported_at", datetime.now(timezone.utc))


@dataclass(frozen=True)
class RunbookStep:
    """A single step in a cutover runbook (Firestore deserialization)."""

    id: str
    name: str
    owner: str
    estimated_duration_minutes: int
    category: StepCategory = StepCategory.PREPARATION
    depends_on: tuple[str, ...] = ()
    order: int = 0


@dataclass(frozen=True)
class TaskProgress:
    """Tracks runtime progress of a single task in a cutover execution."""

    task_id: str
    task_name: str
    status: TaskProgressStatus = TaskProgressStatus.NOT_STARTED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None


@dataclass(frozen=True)
class GateDecision:
    """Records a go/no-go gate decision during cutover execution."""

    gate_id: str
    decision: str  # GO | NO_GO | OVERRIDE
    decided_by: str = ""
    decided_at: datetime | None = None
    notes: str | None = None


@dataclass(frozen=True)
class KnowledgeEntry:
    """A lessons-learned or knowledge-base entry captured during cutover/hypercare."""

    id: str
    title: str
    category: str
    content: str
    source_task_id: str | None = None
    created_at: datetime = None  # type: ignore[assignment]
    created_by: str = ""

    def __post_init__(self) -> None:
        if self.created_at is None:
            from datetime import timezone

            object.__setattr__(self, "created_at", datetime.now(timezone.utc))
