"""LessonsLearnedService — analyses cutover deviations and hypercare incidents
to auto-generate knowledge-base entries for future migrations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.entities.cutover_execution import CutoverExecution
from domain.value_objects.cutover_types import (
    HypercareIncident,
    KnowledgeEntry,
)


class LessonsLearnedService:
    """Pure domain service — no infrastructure dependencies."""

    def generate_lessons_learned(
        self,
        execution: CutoverExecution,
        incidents: list[HypercareIncident],
    ) -> list[KnowledgeEntry]:
        """Analyse deviations and incidents to produce structured lessons-learned entries."""
        entries: list[KnowledgeEntry] = []
        now = datetime.now(timezone.utc)

        # --- Analyse execution deviations ---
        entries.extend(self._analyse_deviations(execution, now))

        # --- Analyse cutover issues ---
        entries.extend(self._analyse_issues(execution, now))

        # --- Analyse hypercare incidents ---
        entries.extend(self._analyse_incidents(incidents, now))

        # --- Generate summary entry if there are findings ---
        if entries:
            entries.append(self._generate_summary(execution, incidents, entries, now))

        return entries

    # ------------------------------------------------------------------
    # Private analysis methods
    # ------------------------------------------------------------------

    def _analyse_deviations(self, execution: CutoverExecution, now: datetime) -> list[KnowledgeEntry]:
        """Turn execution deviations into knowledge entries."""
        entries: list[KnowledgeEntry] = []

        # Group deviations by type
        deviation_groups: dict[str, list] = {}
        for dev in execution.deviations:
            deviation_groups.setdefault(dev.deviation_type, []).append(dev)

        for dev_type, devs in deviation_groups.items():
            if dev_type == "DELAY":
                entries.append(
                    KnowledgeEntry(
                        id=str(uuid.uuid4()),
                        title=f"Cutover delays observed ({len(devs)} tasks)",
                        category="SCHEDULE",
                        content=self._format_delay_content(devs),
                        source_task_id=devs[0].task_id if devs else None,
                        created_at=now,
                        created_by="system:lessons_learned_service",
                    )
                )
            elif dev_type == "FAILURE":
                entries.append(
                    KnowledgeEntry(
                        id=str(uuid.uuid4()),
                        title=f"Task failures during cutover ({len(devs)} occurrences)",
                        category="FAILURE_ANALYSIS",
                        content=self._format_failure_content(devs),
                        source_task_id=devs[0].task_id if devs else None,
                        created_at=now,
                        created_by="system:lessons_learned_service",
                    )
                )
            elif dev_type == "SKIP":
                entries.append(
                    KnowledgeEntry(
                        id=str(uuid.uuid4()),
                        title=f"Skipped tasks during cutover ({len(devs)} tasks)",
                        category="PROCESS_IMPROVEMENT",
                        content=self._format_skip_content(devs),
                        source_task_id=devs[0].task_id if devs else None,
                        created_at=now,
                        created_by="system:lessons_learned_service",
                    )
                )
            elif dev_type == "MANUAL_OVERRIDE":
                entries.append(
                    KnowledgeEntry(
                        id=str(uuid.uuid4()),
                        title=f"Manual overrides applied ({len(devs)} instances)",
                        category="RISK_MANAGEMENT",
                        content=self._format_override_content(devs),
                        source_task_id=devs[0].task_id if devs else None,
                        created_at=now,
                        created_by="system:lessons_learned_service",
                    )
                )
            elif dev_type == "REORDER":
                entries.append(
                    KnowledgeEntry(
                        id=str(uuid.uuid4()),
                        title=f"Task reordering during cutover ({len(devs)} changes)",
                        category="PROCESS_IMPROVEMENT",
                        content=self._format_reorder_content(devs),
                        source_task_id=devs[0].task_id if devs else None,
                        created_at=now,
                        created_by="system:lessons_learned_service",
                    )
                )

        return entries

    def _analyse_issues(self, execution: CutoverExecution, now: datetime) -> list[KnowledgeEntry]:
        """Turn cutover issues into knowledge entries."""
        entries: list[KnowledgeEntry] = []

        critical_issues = [i for i in execution.issues if i.severity == "CRITICAL"]
        high_issues = [i for i in execution.issues if i.severity == "HIGH"]

        if critical_issues:
            entries.append(
                KnowledgeEntry(
                    id=str(uuid.uuid4()),
                    title=f"Critical issues encountered ({len(critical_issues)})",
                    category="INCIDENT_ANALYSIS",
                    content=self._format_issue_content(critical_issues),
                    created_at=now,
                    created_by="system:lessons_learned_service",
                )
            )

        if high_issues:
            entries.append(
                KnowledgeEntry(
                    id=str(uuid.uuid4()),
                    title=f"High-severity issues encountered ({len(high_issues)})",
                    category="INCIDENT_ANALYSIS",
                    content=self._format_issue_content(high_issues),
                    created_at=now,
                    created_by="system:lessons_learned_service",
                )
            )

        return entries

    def _analyse_incidents(self, incidents: list[HypercareIncident], now: datetime) -> list[KnowledgeEntry]:
        """Turn hypercare incidents into knowledge entries."""
        entries: list[KnowledgeEntry] = []
        if not incidents:
            return entries

        # Group by SAP component
        by_component: dict[str, list[HypercareIncident]] = {}
        for inc in incidents:
            comp = inc.sap_component or "UNKNOWN"
            by_component.setdefault(comp, []).append(inc)

        for component, component_incidents in by_component.items():
            entries.append(
                KnowledgeEntry(
                    id=str(uuid.uuid4()),
                    title=f"Hypercare incidents for {component} ({len(component_incidents)} total)",
                    category="HYPERCARE_ANALYSIS",
                    content=self._format_incident_content(component, component_incidents),
                    created_at=now,
                    created_by="system:lessons_learned_service",
                )
            )

        # Add recurring pattern analysis
        recurring = self._find_recurring_patterns(incidents)
        if recurring:
            entries.append(
                KnowledgeEntry(
                    id=str(uuid.uuid4()),
                    title="Recurring incident patterns identified",
                    category="PATTERN_ANALYSIS",
                    content=recurring,
                    created_at=now,
                    created_by="system:lessons_learned_service",
                )
            )

        return entries

    def _generate_summary(
        self,
        execution: CutoverExecution,
        incidents: list[HypercareIncident],
        entries: list[KnowledgeEntry],
        now: datetime,
    ) -> KnowledgeEntry:
        """Generate a summary knowledge entry aggregating all findings."""
        total_deviations = len(execution.deviations)
        total_issues = len(execution.issues)
        total_incidents = len(incidents)
        was_aborted = execution.status.value == "ABORTED"

        duration_info = f"Planned: {execution.planned_duration_minutes} min, Actual: {execution.elapsed_minutes} min"
        variance = execution.elapsed_minutes - execution.planned_duration_minutes
        variance_pct = (
            round((variance / execution.planned_duration_minutes) * 100, 1)
            if execution.planned_duration_minutes > 0
            else 0
        )

        lines = [
            "CUTOVER LESSONS LEARNED SUMMARY",
            "=" * 40,
            f"Execution Status: {execution.status.value}",
            f"Duration: {duration_info} (variance: {variance_pct}%)",
            f"Total Deviations: {total_deviations}",
            f"Total Cutover Issues: {total_issues}",
            f"Total Hypercare Incidents: {total_incidents}",
            f"Knowledge Entries Generated: {len(entries)}",
            "",
        ]

        if was_aborted:
            lines.append("WARNING: Cutover was aborted. Review abort reason carefully.")
            lines.append("")

        # Key recommendations
        lines.append("KEY RECOMMENDATIONS:")
        if variance_pct > 20:
            lines.append("- Duration significantly exceeded plan. Review estimation methodology.")
        if total_deviations > 5:
            lines.append("- High deviation count suggests runbook needs refinement for next migration.")
        if any(i.severity == "CRITICAL" for i in execution.issues):
            lines.append("- Critical issues occurred. Strengthen pre-cutover validation and testing.")
        if total_incidents > 10:
            lines.append("- High incident count in hypercare. Extend user training and support.")

        categories = {e.category for e in entries}
        lines.append(f"\nCategories covered: {', '.join(sorted(categories))}")

        return KnowledgeEntry(
            id=str(uuid.uuid4()),
            title="Cutover Lessons Learned — Executive Summary",
            category="EXECUTIVE_SUMMARY",
            content="\n".join(lines),
            created_at=now,
            created_by="system:lessons_learned_service",
        )

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_delay_content(devs: list) -> str:
        lines = ["Tasks that experienced delays during cutover:\n"]
        for d in devs:
            lines.append(f"- Task {d.task_id}: planned={d.planned_value}, actual={d.actual_value}, impact={d.impact}")
        lines.append(
            "\nRecommendation: Review duration estimates for these task types and add buffer time in future runbooks."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_failure_content(devs: list) -> str:
        lines = ["Tasks that failed during cutover:\n"]
        for d in devs:
            lines.append(f"- Task {d.task_id}: expected={d.planned_value}, result={d.actual_value}, impact={d.impact}")
        lines.append(
            "\nRecommendation: Strengthen pre-cutover testing for these task "
            "categories. Consider adding automated retry logic."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_skip_content(devs: list) -> str:
        lines = ["Tasks that were skipped during cutover:\n"]
        for d in devs:
            lines.append(f"- Task {d.task_id}: reason={d.actual_value}, impact={d.impact}")
        lines.append(
            "\nRecommendation: Evaluate whether skipped tasks should be removed from the runbook or made conditional."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_override_content(devs: list) -> str:
        lines = ["Manual overrides applied during cutover:\n"]
        for d in devs:
            lines.append(f"- Task {d.task_id}: override from={d.planned_value} to={d.actual_value}, impact={d.impact}")
        lines.append("\nRecommendation: Review whether overrides indicate process gaps or insufficient pre-planning.")
        return "\n".join(lines)

    @staticmethod
    def _format_reorder_content(devs: list) -> str:
        lines = ["Tasks reordered during cutover:\n"]
        for d in devs:
            lines.append(
                f"- Task {d.task_id}: planned order={d.planned_value}, actual order={d.actual_value}, impact={d.impact}"
            )
        lines.append("\nRecommendation: Update runbook task dependencies to reflect the actual execution order.")
        return "\n".join(lines)

    @staticmethod
    def _format_issue_content(issues: list) -> str:
        lines = []
        for issue in issues:
            status = "RESOLVED" if issue.resolved_at else "OPEN"
            lines.append(
                f"- [{issue.severity}] {issue.description} (task: {issue.affected_task_id or 'N/A'}, status: {status})"
            )
            if issue.resolution:
                lines.append(f"  Resolution: {issue.resolution}")
        return "\n".join(lines)

    @staticmethod
    def _format_incident_content(component: str, incidents: list[HypercareIncident]) -> str:
        lines = [f"Incidents for SAP component {component}:\n"]
        for inc in incidents:
            status = "RESOLVED" if inc.resolved_at else "OPEN"
            lines.append(f"- [{inc.severity}] {inc.description} (ticket: {inc.ticket_id or 'N/A'}, status: {status})")
            if inc.resolution:
                lines.append(f"  Resolution: {inc.resolution}")
        return "\n".join(lines)

    @staticmethod
    def _find_recurring_patterns(incidents: list[HypercareIncident]) -> str:
        """Identify recurring patterns from incident descriptions."""
        if len(incidents) < 2:
            return ""

        # Simple keyword frequency analysis
        keywords: dict[str, int] = {}
        for inc in incidents:
            words = inc.description.lower().split()
            for word in words:
                if len(word) > 4:  # Skip short/common words
                    keywords[word] = keywords.get(word, 0) + 1

        recurring = {k: v for k, v in keywords.items() if v >= 2}
        if not recurring:
            return ""

        sorted_keywords = sorted(recurring.items(), key=lambda x: x[1], reverse=True)[:10]
        lines = ["Frequently occurring terms across incidents:\n"]
        for keyword, count in sorted_keywords:
            lines.append(f"- '{keyword}': appeared in {count} incidents")
        lines.append(
            "\nRecommendation: Investigate root causes related to these recurring themes to prevent future incidents."
        )
        return "\n".join(lines)
