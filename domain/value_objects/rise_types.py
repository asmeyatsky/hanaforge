"""RISE with SAP value objects — immutable data carriers for SAP integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class RISEConnectionMode(Enum):
    RFC = "RFC"
    ODATA = "ODATA"


class RISESystemType(Enum):
    ECC = "ECC"
    S4HANA_ON_PREMISE = "S4HANA_ON_PREMISE"
    S4HANA_CLOUD = "S4HANA_CLOUD"
    BW = "BW"
    CRM = "CRM"
    SRM = "SRM"


class TransportStatus(Enum):
    RELEASED = "RELEASED"
    MODIFIABLE = "MODIFIABLE"
    IMPORTED = "IMPORTED"
    IMPORT_FAILED = "IMPORT_FAILED"


class ReadinessCheckSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ReadinessCheckStatus(Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class OverallReadinessStatus(Enum):
    READY = "READY"
    CONDITIONAL = "CONDITIONAL"
    NOT_READY = "NOT_READY"


@dataclass(frozen=True)
class RISEConnection:
    """Connection parameters for a RISE with SAP managed system."""

    host: str
    port: int
    client: str
    user: str
    system_type: RISESystemType
    mode: RISEConnectionMode = RISEConnectionMode.ODATA

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("host must not be empty")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"port must be between 1 and 65535, got {self.port}")
        if not self.client:
            raise ValueError("client must not be empty")
        if not self.user:
            raise ValueError("user must not be empty")


@dataclass(frozen=True)
class SAPSystemInfo:
    """Snapshot of SAP system metadata retrieved via RISE integration."""

    system_id: str
    version: str
    db_type: str
    db_size_gb: float
    num_users: int
    kernel_version: str
    unicode_enabled: bool


@dataclass(frozen=True)
class TransportRequest:
    """A single SAP transport request with its contained objects."""

    id: str
    description: str
    owner: str
    status: TransportStatus
    created_at: datetime
    objects: tuple[str, ...]


@dataclass(frozen=True)
class TransportResult:
    """Outcome of executing a transport request."""

    transport_id: str
    success: bool
    return_code: int
    messages: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessCheckItem:
    """A single readiness check with its result."""

    name: str
    status: ReadinessCheckStatus
    message: str
    severity: ReadinessCheckSeverity


@dataclass(frozen=True)
class ReadinessCheckResult:
    """Aggregate result of all RISE readiness checks for a system."""

    overall_status: OverallReadinessStatus
    checks: tuple[ReadinessCheckItem, ...]

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == ReadinessCheckStatus.PASSED)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == ReadinessCheckStatus.FAILED)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.status == ReadinessCheckStatus.WARNING)
