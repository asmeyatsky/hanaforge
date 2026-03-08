"""SimpleReportGenerator — implements ReportGeneratorPort with structured text output.

Generates plain-text assessment reports and executive summaries.  A future
iteration can use reportlab or WeasyPrint to produce PDF output.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from domain.entities.programme import Programme
from domain.value_objects.complexity_score import ComplexityScore
from domain.value_objects.object_type import CompatibilityStatus


class SimpleReportGenerator:
    """Implements ReportGeneratorPort with structured text reports."""

    async def generate_assessment_report(
        self,
        programme: Programme,
        landscapes: list[Any],
        objects: list[Any],
        remediations: list[Any],
    ) -> bytes:
        """Generate a full assessment report as UTF-8 text bytes."""
        lines: list[str] = []

        # Header
        lines.append("=" * 72)
        lines.append("HANAFORGE - S/4HANA MIGRATION ASSESSMENT REPORT")
        lines.append("=" * 72)
        lines.append("")
        lines.append(f"Programme:        {programme.name}")
        lines.append(f"Programme ID:     {programme.id}")
        lines.append(f"Customer ID:      {programme.customer_id}")
        lines.append(f"Source Version:    {programme.sap_source_version}")
        lines.append(f"Target Version:   {programme.target_version}")
        lines.append(f"Status:           {programme.status.value}")
        lines.append(
            f"Generated:        {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )
        lines.append("")

        # Complexity score
        if programme.complexity_score is not None:
            lines.append("-" * 72)
            lines.append("COMPLEXITY ASSESSMENT")
            lines.append("-" * 72)
            lines.append(f"  Score:      {programme.complexity_score.score}/100")
            lines.append(f"  Risk Level: {programme.complexity_score.risk_level}")
            if programme.complexity_score.benchmark_percentile is not None:
                lines.append(
                    f"  Percentile: {programme.complexity_score.benchmark_percentile:.1f}%"
                )
            lines.append("")

        # Landscape summary
        lines.append("-" * 72)
        lines.append("LANDSCAPE SUMMARY")
        lines.append("-" * 72)
        if landscapes:
            for ls in landscapes:
                system_id = getattr(ls, "system_id", "N/A")
                system_role = getattr(ls, "system_role", "N/A")
                db_size = getattr(ls, "db_size_gb", 0)
                users = getattr(ls, "number_of_users", 0)
                obj_count = getattr(ls, "custom_object_count", 0)
                lines.append(f"  System: {system_id} ({system_role})")
                lines.append(f"    DB Size:        {db_size:.1f} GB")
                lines.append(f"    Users:          {users}")
                lines.append(f"    Custom Objects: {obj_count}")
                lines.append("")
        else:
            lines.append("  No landscapes discovered yet.")
            lines.append("")

        # Object analysis summary
        lines.append("-" * 72)
        lines.append("CUSTOM OBJECT ANALYSIS")
        lines.append("-" * 72)
        total = len(objects)
        compatible = sum(
            1
            for o in objects
            if getattr(o, "compatibility_status", None) == CompatibilityStatus.COMPATIBLE
        )
        incompatible = sum(
            1
            for o in objects
            if getattr(o, "compatibility_status", None) == CompatibilityStatus.INCOMPATIBLE
        )
        needs_review = sum(
            1
            for o in objects
            if getattr(o, "compatibility_status", None) == CompatibilityStatus.NEEDS_REVIEW
        )
        unknown = total - compatible - incompatible - needs_review

        lines.append(f"  Total Objects:   {total}")
        lines.append(f"  Compatible:      {compatible}")
        lines.append(f"  Incompatible:    {incompatible}")
        lines.append(f"  Needs Review:    {needs_review}")
        lines.append(f"  Unknown:         {unknown}")
        lines.append("")

        # Incompatible objects detail
        if incompatible > 0:
            lines.append("-" * 72)
            lines.append("INCOMPATIBLE OBJECTS (requiring remediation)")
            lines.append("-" * 72)
            for o in objects:
                if getattr(o, "compatibility_status", None) == CompatibilityStatus.INCOMPATIBLE:
                    name = getattr(o, "object_name", "N/A")
                    obj_type = getattr(o, "object_type", "N/A")
                    apis = getattr(o, "deprecated_apis", ())
                    lines.append(f"  {name} ({obj_type})")
                    if apis:
                        lines.append(f"    Deprecated APIs: {', '.join(apis)}")
                    lines.append("")

        # Remediation summary
        lines.append("-" * 72)
        lines.append("REMEDIATION SUGGESTIONS")
        lines.append("-" * 72)
        lines.append(f"  Total Suggestions: {len(remediations)}")
        if remediations:
            for r in remediations:
                issue = getattr(r, "issue_type", "N/A")
                api = getattr(r, "deprecated_api", "N/A")
                replacement = getattr(r, "suggested_replacement", "N/A")
                confidence = getattr(r, "confidence_score", 0.0)
                lines.append(f"  - {issue}: {api}")
                lines.append(f"    Replacement: {replacement}")
                lines.append(f"    Confidence:  {confidence:.0%}")
                lines.append("")
        else:
            lines.append("  No remediation suggestions generated yet.")
            lines.append("")

        # Footer
        lines.append("=" * 72)
        lines.append("END OF REPORT")
        lines.append("=" * 72)

        report_text = "\n".join(lines)
        return report_text.encode("utf-8")

    async def generate_executive_summary(
        self,
        programme: Programme,
        complexity: ComplexityScore,
    ) -> str:
        """Generate a concise executive summary string."""
        go_live_str = (
            programme.go_live_date.strftime("%Y-%m-%d")
            if programme.go_live_date
            else "Not set"
        )

        summary = (
            f"Executive Summary: {programme.name}\n"
            f"{'=' * 50}\n\n"
            f"Migration programme '{programme.name}' for customer {programme.customer_id} "
            f"targets a migration from SAP {programme.sap_source_version} to "
            f"{programme.target_version}.\n\n"
            f"Current Status: {programme.status.value}\n"
            f"Go-Live Target: {go_live_str}\n\n"
            f"Complexity Assessment:\n"
            f"  Overall Score: {complexity.score}/100 ({complexity.risk_level})\n"
        )

        if complexity.benchmark_percentile is not None:
            summary += (
                f"  Benchmark Percentile: {complexity.benchmark_percentile:.1f}% "
                f"(compared to similar migrations)\n"
            )

        if complexity.risk_level == "CRITICAL":
            summary += (
                "\nRecommendation: This migration carries CRITICAL risk. "
                "Consider a phased approach with extensive testing and "
                "dedicated remediation sprints before go-live.\n"
            )
        elif complexity.risk_level == "HIGH":
            summary += (
                "\nRecommendation: This migration carries HIGH risk. "
                "Allocate additional buffer time and ensure senior ABAP "
                "developers are available for remediation.\n"
            )
        elif complexity.risk_level == "MEDIUM":
            summary += (
                "\nRecommendation: This migration has MEDIUM complexity. "
                "Standard migration timeline should be achievable with "
                "proper planning and automated remediation support.\n"
            )
        else:
            summary += (
                "\nRecommendation: This migration has LOW complexity. "
                "An accelerated timeline may be feasible with AI-assisted "
                "code remediation.\n"
            )

        return summary
