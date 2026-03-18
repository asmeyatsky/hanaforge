"""Tests for HypercareSession and LessonsLearnedService — pure domain logic, no mocks."""

from datetime import datetime, timedelta, timezone

import pytest

from domain.entities.cutover_execution import CutoverExecution
from domain.entities.hypercare_session import HypercareSession
from domain.services.lessons_learned_service import LessonsLearnedService
from domain.value_objects.cutover_types import (
    CutoverIssue,
    ExecutionDeviation,
    ExecutionStatus,
    HypercareIncident,
    HypercareStatus,
    KnowledgeEntry,
    MonitoringConfig,
    TaskExecution,
)


def _make_session(
    *,
    status: HypercareStatus = HypercareStatus.ACTIVE,
) -> HypercareSession:
    now = datetime.now(timezone.utc)
    return HypercareSession(
        id="hc-001",
        programme_id="prog-001",
        start_date=now,
        end_date=now + timedelta(days=90),
        status=status,
        monitoring_config=MonitoringConfig(
            alert_channels=("email", "slack"),
            check_interval_minutes=15,
            escalation_contacts=("manager@acme.com",),
            sla_response_minutes=30,
        ),
        created_at=now,
    )


class TestStartHypercareSession:
    def test_start_hypercare_session(self) -> None:
        session = _make_session()

        assert session.id == "hc-001"
        assert session.programme_id == "prog-001"
        assert session.status == HypercareStatus.ACTIVE
        assert len(session.incidents) == 0
        assert len(session.knowledge_entries) == 0
        assert session.monitoring_config.check_interval_minutes == 15

    def test_session_has_90_day_window(self) -> None:
        session = _make_session()
        duration = session.end_date - session.start_date
        assert duration.days == 90


class TestLogIncident:
    def test_log_incident(self) -> None:
        session = _make_session()
        now = datetime.now(timezone.utc)

        incident = HypercareIncident(
            id="INC-001",
            severity="HIGH",
            description="Users cannot access Fiori launchpad",
            sap_component="BC-FES",
            reported_at=now,
        )

        updated = session.log_incident(incident)

        assert len(updated.incidents) == 1
        assert updated.incidents[0].id == "INC-001"
        assert updated.incidents[0].severity == "HIGH"
        assert updated.status == HypercareStatus.ACTIVE  # HIGH does not escalate
        # Original unchanged
        assert len(session.incidents) == 0

    def test_critical_incident_escalates_session(self) -> None:
        session = _make_session()
        now = datetime.now(timezone.utc)

        incident = HypercareIncident(
            id="INC-002",
            severity="CRITICAL",
            description="HANA database unresponsive",
            sap_component="BC-DB-HDB",
            reported_at=now,
        )

        updated = session.log_incident(incident)

        assert updated.status == HypercareStatus.ESCALATED

    def test_multiple_incidents(self) -> None:
        session = _make_session()
        now = datetime.now(timezone.utc)

        i1 = HypercareIncident(
            id="INC-001",
            severity="LOW",
            description="Slow report",
            reported_at=now,
        )
        i2 = HypercareIncident(
            id="INC-002",
            severity="MEDIUM",
            description="Batch job delayed",
            reported_at=now,
        )

        updated = session.log_incident(i1).log_incident(i2)
        assert len(updated.incidents) == 2


class TestCaptureKnowledge:
    def test_capture_knowledge(self) -> None:
        session = _make_session()
        now = datetime.now(timezone.utc)

        entry = KnowledgeEntry(
            id="KE-001",
            title="RFC timeout workaround",
            category="TECHNICAL",
            content="Increase timeout to 60s for cross-system RFC calls",
            created_at=now,
            created_by="basis_admin",
        )

        updated = session.capture_knowledge(entry)

        assert len(updated.knowledge_entries) == 1
        assert updated.knowledge_entries[0].title == "RFC timeout workaround"
        # Original unchanged
        assert len(session.knowledge_entries) == 0


class TestCloseSession:
    def test_close_session(self) -> None:
        session = _make_session()

        closed = session.close_session()

        assert closed.status == HypercareStatus.CLOSED

    def test_cannot_close_already_closed(self) -> None:
        session = _make_session(status=HypercareStatus.CLOSED)
        with pytest.raises(ValueError, match="already closed"):
            session.close_session()


class TestResolveIncident:
    def test_resolve_incident(self) -> None:
        session = _make_session()
        now = datetime.now(timezone.utc)

        incident = HypercareIncident(
            id="INC-001",
            severity="HIGH",
            description="Report failure",
            reported_at=now,
        )
        with_incident = session.log_incident(incident)

        resolved = with_incident.resolve_incident("INC-001", "Fixed query index")

        assert resolved.incidents[0].resolved_at is not None
        assert resolved.incidents[0].resolution == "Fixed query index"

    def test_resolve_critical_deescalates(self) -> None:
        session = _make_session()
        now = datetime.now(timezone.utc)

        incident = HypercareIncident(
            id="INC-001",
            severity="CRITICAL",
            description="HANA down",
            reported_at=now,
        )
        escalated = session.log_incident(incident)
        assert escalated.status == HypercareStatus.ESCALATED

        resolved = escalated.resolve_incident("INC-001", "HANA restarted")
        assert resolved.status == HypercareStatus.ACTIVE


class TestGenerateLessonsLearned:
    def _make_execution_with_deviations(self) -> CutoverExecution:
        now = datetime.now(timezone.utc)
        return CutoverExecution(
            id="exec-001",
            runbook_id="rb-001",
            programme_id="prog-001",
            started_at=now - timedelta(hours=12),
            status=ExecutionStatus.COMPLETED,
            task_statuses=(
                TaskExecution(task_id="T-001", task_name="Backup", status="COMPLETED"),
                TaskExecution(task_id="T-002", task_name="Migration", status="COMPLETED"),
            ),
            deviations=(
                ExecutionDeviation(
                    task_id="T-001",
                    deviation_type="DELAY",
                    planned_value="120 min",
                    actual_value="180 min",
                    impact="60 minute delay",
                    recorded_at=now,
                ),
                ExecutionDeviation(
                    task_id="T-002",
                    deviation_type="FAILURE",
                    planned_value="SUCCESS",
                    actual_value="FAILED_RETRY_OK",
                    impact="Required manual intervention",
                    recorded_at=now,
                ),
            ),
            issues=(
                CutoverIssue(
                    id="ISS-001",
                    severity="CRITICAL",
                    description="RFC timeout during data load",
                    affected_task_id="T-002",
                    raised_at=now,
                ),
            ),
            elapsed_minutes=720,
            planned_duration_minutes=480,
        )

    def test_generate_lessons_learned(self) -> None:
        service = LessonsLearnedService()
        execution = self._make_execution_with_deviations()
        now = datetime.now(timezone.utc)

        incidents = [
            HypercareIncident(
                id="INC-001",
                severity="HIGH",
                description="Fiori tiles missing after migration",
                sap_component="BC-FES",
                reported_at=now,
            ),
            HypercareIncident(
                id="INC-002",
                severity="MEDIUM",
                description="Batch job scheduling offset after migration",
                sap_component="BC-CCM",
                reported_at=now,
            ),
        ]

        entries = service.generate_lessons_learned(execution, incidents)

        assert len(entries) > 0, "Should generate at least one entry"

        # Should have entries for deviations, issues, and incidents
        categories = {e.category for e in entries}
        assert "SCHEDULE" in categories, "Should have delay analysis"
        assert "FAILURE_ANALYSIS" in categories, "Should have failure analysis"
        assert "INCIDENT_ANALYSIS" in categories, "Should have issue analysis"
        assert "HYPERCARE_ANALYSIS" in categories, "Should have hypercare analysis"
        assert "EXECUTIVE_SUMMARY" in categories, "Should have summary"

    def test_generate_lessons_learned_empty_inputs(self) -> None:
        service = LessonsLearnedService()
        now = datetime.now(timezone.utc)
        execution = CutoverExecution(
            id="exec-002",
            runbook_id="rb-001",
            programme_id="prog-001",
            started_at=now - timedelta(hours=6),
            status=ExecutionStatus.COMPLETED,
            task_statuses=(),
            elapsed_minutes=360,
            planned_duration_minutes=480,
        )

        entries = service.generate_lessons_learned(execution, [])
        # With no deviations, issues, or incidents, no entries generated
        assert len(entries) == 0

    def test_summary_includes_duration_variance(self) -> None:
        service = LessonsLearnedService()
        execution = self._make_execution_with_deviations()

        entries = service.generate_lessons_learned(execution, [])

        summary = next((e for e in entries if e.category == "EXECUTIVE_SUMMARY"), None)
        assert summary is not None
        assert "variance" in summary.content.lower()
        assert "720" in summary.content or "Actual: 720" in summary.content

    def test_lessons_learned_all_entries_have_required_fields(self) -> None:
        service = LessonsLearnedService()
        execution = self._make_execution_with_deviations()
        now = datetime.now(timezone.utc)

        incidents = [
            HypercareIncident(
                id="INC-001",
                severity="LOW",
                description="Minor display issue",
                reported_at=now,
            ),
        ]

        entries = service.generate_lessons_learned(execution, incidents)

        for entry in entries:
            assert entry.id, "Entry must have an ID"
            assert entry.title, "Entry must have a title"
            assert entry.category, "Entry must have a category"
            assert entry.content, "Entry must have content"
            assert entry.created_at is not None, "Entry must have created_at"
            assert entry.created_by, "Entry must have created_by"


class TestSessionImmutability:
    def test_session_is_immutable(self) -> None:
        original = _make_session()
        now = datetime.now(timezone.utc)

        incident = HypercareIncident(
            id="INC-001",
            severity="LOW",
            description="Test",
            reported_at=now,
        )
        updated = original.log_incident(incident)

        assert len(original.incidents) == 0
        assert len(updated.incidents) == 1
        assert original is not updated
