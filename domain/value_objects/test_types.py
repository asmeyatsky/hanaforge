"""Test-related value objects — enums and frozen dataclasses for TestForge SAP Edition."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProcessArea(Enum):
    ORDER_TO_CASH = "ORDER_TO_CASH"
    PROCURE_TO_PAY = "PROCURE_TO_PAY"
    RECORD_TO_REPORT = "RECORD_TO_REPORT"
    HIRE_TO_RETIRE = "HIRE_TO_RETIRE"
    PLAN_TO_PRODUCE = "PLAN_TO_PRODUCE"
    CROSS_PROCESS = "CROSS_PROCESS"
    INTEGRATION = "INTEGRATION"


class TestPriority(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TestStatus(Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class TestStep:
    step_number: int
    action: str
    expected_result: str
    sap_transaction: str | None = None
    test_data: str | None = None


class TestExportFormat(Enum):
    JIRA_XRAY = "JIRA_XRAY"
    AZURE_DEVOPS = "AZURE_DEVOPS"
    HP_ALM = "HP_ALM"
    TRICENTIS_TOSCA = "TRICENTIS_TOSCA"
    CSV = "CSV"


@dataclass(frozen=True)
class TraceabilityEntry:
    process_id: str
    process_name: str
    test_scenario_id: str
    test_scenario_name: str
    defect_ids: tuple[str, ...] = ()
    coverage_status: str = "COVERED"


class InterfaceTestType(Enum):
    IDOC = "IDOC"
    RFC = "RFC"
    BAPI = "BAPI"
    REST_API = "REST_API"
    ODATA = "ODATA"
