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

    async def generate_board_presentation(
        self,
        programme: Programme,
        landscapes: list[Any],
        objects: list[Any],
        remediations: list[Any],
        complexity: ComplexityScore,
        recommendation: str,
    ) -> bytes:
        """Generate a board-presentation scope document as portable HTML bytes."""
        generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        go_live_str = (
            programme.go_live_date.strftime("%Y-%m-%d")
            if programme.go_live_date
            else "Not set"
        )

        # --- Compute statistics ---
        total_objects = len(objects)
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
        unknown = total_objects - compatible - incompatible - needs_review

        # Objects by domain
        domain_counts: dict[str, int] = {}
        for o in objects:
            domain_name = getattr(getattr(o, "domain", None), "value", "UNKNOWN")
            domain_counts[domain_name] = domain_counts.get(domain_name, 0) + 1

        # Objects by compatibility status
        status_counts = {
            "Compatible": compatible,
            "Incompatible": incompatible,
            "Needs Review": needs_review,
            "Unknown": unknown,
        }

        # Integration points across all landscapes
        all_integration_points: list[str] = []
        total_db_size = 0.0
        total_users = 0
        for ls in landscapes:
            ips = getattr(ls, "integration_points", ())
            all_integration_points.extend(ips)
            total_db_size += getattr(ls, "db_size_gb", 0.0)
            total_users += getattr(ls, "number_of_users", 0)

        # Risk colour mapping
        risk_colours = {
            "LOW": "#27ae60",
            "MEDIUM": "#f39c12",
            "HIGH": "#e67e22",
            "CRITICAL": "#e74c3c",
        }
        risk_colour = risk_colours.get(complexity.risk_level, "#95a5a6")

        # Timeline recommendation based on complexity
        timeline_map = {
            "LOW": ("6-9 months", "Accelerated migration feasible with AI-assisted remediation."),
            "MEDIUM": ("9-14 months", "Standard migration timeline with proper planning and automated support."),
            "HIGH": ("14-20 months", "Extended timeline recommended with phased approach and senior ABAP resources."),
            "CRITICAL": (
                "20-30 months",
                "Multi-phase programme required with extensive testing, "
                "dedicated remediation sprints, and executive oversight.",
            ),
        }
        timeline_duration, timeline_note = timeline_map.get(
            complexity.risk_level, ("12-18 months", "Standard timeline.")
        )

        # --- Build HTML ---
        domain_rows = "\n".join(
            f"<tr><td>{d}</td><td style='text-align:right'>{c}</td></tr>"
            for d, c in sorted(domain_counts.items(), key=lambda x: -x[1])
        )

        status_bar_items = ""
        status_bar_colours = {
            "Compatible": "#27ae60",
            "Incompatible": "#e74c3c",
            "Needs Review": "#f39c12",
            "Unknown": "#95a5a6",
        }
        for label, count in status_counts.items():
            pct = (count / total_objects * 100) if total_objects > 0 else 0
            if pct > 0:
                status_bar_items += (
                    f"<div style='width:{pct:.1f}%;background:{status_bar_colours[label]};"
                    f"height:28px;display:inline-block;' title='{label}: {count}'></div>"
                )

        status_legend = " &nbsp; ".join(
            f"<span style='display:inline-block;width:12px;height:12px;"
            f"background:{status_bar_colours[label]};border-radius:2px;"
            f"vertical-align:middle;margin-right:4px;'></span>{label}: {count}"
            for label, count in status_counts.items()
        )

        landscape_rows = "\n".join(
            f"<tr>"
            f"<td>{getattr(ls, 'system_id', 'N/A')}</td>"
            f"<td>{getattr(getattr(ls, 'system_role', None), 'value', 'N/A')}</td>"
            f"<td style='text-align:right'>{getattr(ls, 'db_size_gb', 0):.1f} GB</td>"
            f"<td style='text-align:right'>{getattr(ls, 'number_of_users', 0):,}</td>"
            f"<td style='text-align:right'>{getattr(ls, 'custom_object_count', 0):,}</td>"
            f"</tr>"
            for ls in landscapes
        )

        integration_list = "\n".join(
            f"<li>{ip}</li>" for ip in sorted(set(all_integration_points))
        ) if all_integration_points else "<li>No integration points discovered</li>"

        risk_items = []
        if incompatible > 0:
            risk_items.append(
                f"<tr><td style='color:#e74c3c;font-weight:600;'>HIGH</td>"
                f"<td>{incompatible} incompatible custom objects require remediation before migration</td>"
                f"<td>Allocate dedicated ABAP remediation sprints</td></tr>"
            )
        if needs_review > 0:
            risk_items.append(
                f"<tr><td style='color:#f39c12;font-weight:600;'>MEDIUM</td>"
                f"<td>{needs_review} objects flagged for manual review may reveal additional incompatibilities</td>"
                f"<td>Complete expert review before finalising scope</td></tr>"
            )
        if total_db_size > 500:
            risk_items.append(
                f"<tr><td style='color:#e67e22;font-weight:600;'>MEDIUM</td>"
                f"<td>Large database size ({total_db_size:.0f} GB) may impact migration window</td>"
                f"<td>Plan data archiving and phased data migration</td></tr>"
            )
        if len(all_integration_points) > 10:
            risk_items.append(
                f"<tr><td style='color:#f39c12;font-weight:600;'>MEDIUM</td>"
                f"<td>{len(all_integration_points)} integration points increase testing complexity</td>"
                f"<td>Establish integration testing environment early</td></tr>"
            )
        if not risk_items:
            risk_items.append(
                "<tr><td style='color:#27ae60;font-weight:600;'>LOW</td>"
                "<td>No critical risks identified at this stage</td>"
                "<td>Continue with standard migration approach</td></tr>"
            )
        risk_rows = "\n".join(risk_items)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Board Presentation — {programme.name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #2c3e50; background: #fff; padding: 40px 60px; line-height: 1.6; }}
  .header {{ border-bottom: 3px solid #2c3e50; padding-bottom: 20px;
    margin-bottom: 30px; }}
  .header h1 {{ font-size: 28px; color: #2c3e50; margin-bottom: 4px; }}
  .header .subtitle {{ font-size: 16px; color: #7f8c8d; }}
  .meta {{ font-size: 13px; color: #95a5a6; margin-top: 8px; }}
  h2 {{ font-size: 20px; color: #2c3e50; margin: 30px 0 15px 0;
    padding-bottom: 8px; border-bottom: 1px solid #ecf0f1; }}
  h2 .section-num {{ color: #3498db; margin-right: 8px; }}
  .summary-box {{ background: #f8f9fa; border-left: 4px solid #3498db;
    padding: 20px 24px; margin: 15px 0; border-radius: 0 4px 4px 0; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 16px; margin: 20px 0; }}
  .kpi {{ background: #f8f9fa; border-radius: 6px;
    padding: 16px 20px; text-align: center; }}
  .kpi .value {{ font-size: 28px; font-weight: 700; color: #2c3e50; }}
  .kpi .label {{ font-size: 12px; color: #7f8c8d;
    text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }}
  .risk-badge {{ display: inline-block; padding: 4px 16px;
    border-radius: 4px; color: #fff; font-weight: 600; font-size: 14px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th, td {{ padding: 10px 14px; text-align: left;
    border-bottom: 1px solid #ecf0f1; font-size: 14px; }}
  th {{ background: #f8f9fa; font-weight: 600; color: #2c3e50; }}
  .status-bar {{ width: 100%; border-radius: 4px; overflow: hidden;
    background: #ecf0f1; font-size: 0; margin: 8px 0; }}
  .legend {{ font-size: 13px; color: #7f8c8d; margin-top: 6px; }}
  ul {{ margin: 8px 0 8px 24px; }}
  li {{ margin: 4px 0; font-size: 14px; }}
  .placeholder {{ background: #fef9e7; border: 1px dashed #f39c12;
    border-radius: 4px; padding: 16px 20px; margin: 12px 0;
    font-size: 14px; color: #7f8c8d; }}
  .footer {{ margin-top: 40px; padding-top: 16px;
    border-top: 1px solid #ecf0f1; font-size: 12px;
    color: #95a5a6; text-align: center; }}
  @media print {{ body {{ padding: 20px 30px; }} }}
</style>
</head>
<body>

<div class="header">
  <h1>S/4HANA Migration — Board Scope Presentation</h1>
  <div class="subtitle">{programme.name} (Customer {programme.customer_id})</div>
  <div class="meta">Programme ID: {programme.id} &bull;
    Generated: {generated} &bull; Status: {programme.status.value}</div>
</div>

<!-- 1. Executive Summary -->
<h2><span class="section-num">01</span>Executive Summary</h2>
<div class="summary-box">
  <p>Migration programme <strong>{programme.name}</strong> targets a transition from
  <strong>SAP {programme.sap_source_version}</strong> to <strong>{programme.target_version}</strong>
  with a go-live target of <strong>{go_live_str}</strong>.</p>
  <p style="margin-top:10px;">Overall complexity is rated
  <span class="risk-badge" style="background:{risk_colour};">{complexity.risk_level}</span>
  with a score of <strong>{complexity.score}/100</strong>\
{f' (percentile: {complexity.benchmark_percentile:.1f}%)' if complexity.benchmark_percentile is not None else ''}.</p>
</div>

<div class="kpi-grid">
  <div class="kpi"><div class="value">{len(landscapes)}</div><div class="label">SAP Systems</div></div>
  <div class="kpi"><div class="value">{total_objects:,}</div><div class="label">Custom Objects</div></div>
  <div class="kpi"><div class="value">{total_db_size:.0f} GB</div><div class="label">Total DB Size</div></div>
  <div class="kpi"><div class="value">{total_users:,}</div><div class="label">Total Users</div></div>
</div>

<!-- 2. Migration Scope & Approach -->
<h2><span class="section-num">02</span>Migration Scope &amp; Approach Recommendation</h2>
<div class="summary-box">
  <p>{recommendation}</p>
</div>

<!-- 3. Complexity Assessment -->
<h2><span class="section-num">03</span>Complexity Assessment</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Overall Score</td><td><strong>{complexity.score}/100</strong></td></tr>
  <tr><td>Risk Level</td><td><span class="risk-badge"
    style="background:{risk_colour};">{complexity.risk_level}</span></td></tr>
  <tr><td>Custom Objects</td><td>{total_objects:,}</td></tr>
  <tr><td>Incompatible Objects</td><td style="color:#e74c3c;font-weight:600;">{incompatible}</td></tr>
  <tr><td>Integration Points</td><td>{len(all_integration_points)}</td></tr>
</table>

<!-- 4. Custom Object Inventory -->
<h2><span class="section-num">04</span>Custom Object Inventory</h2>
<h3 style="font-size:15px;margin:12px 0 8px;">By Compatibility Status</h3>
<div class="status-bar">{status_bar_items}</div>
<div class="legend">{status_legend}</div>

<h3 style="font-size:15px;margin:18px 0 8px;">By Business Domain</h3>
<table>
  <tr><th>Domain</th><th style="text-align:right">Objects</th></tr>
  {domain_rows}
</table>

<!-- 5. Integration Point Summary -->
<h2><span class="section-num">05</span>Integration Point Summary</h2>
<p style="font-size:14px;color:#7f8c8d;margin-bottom:8px;">\
{len(all_integration_points)} integration point(s) across \
{len(landscapes)} system(s):</p>
<ul>{integration_list}</ul>

<!-- 6. Landscape Overview -->
<h2><span class="section-num">06</span>Landscape Overview</h2>
<table>
  <tr><th>System ID</th><th>Role</th><th style="text-align:right">DB Size</th>
  <th style="text-align:right">Users</th>
  <th style="text-align:right">Custom Objects</th></tr>
  {landscape_rows}
</table>

<!-- 7. Timeline Recommendation -->
<h2><span class="section-num">07</span>Timeline Recommendation</h2>
<div class="summary-box">
  <p><strong>Estimated Duration:</strong> {timeline_duration}</p>
  <p style="margin-top:8px;">{timeline_note}</p>
</div>

<!-- 8. Risk Register -->
<h2><span class="section-num">08</span>Risk Register</h2>
<table>
  <tr><th style="width:100px;">Severity</th><th>Risk</th><th>Mitigation</th></tr>
  {risk_rows}
</table>

<!-- 9. Budget Estimate -->
<h2><span class="section-num">09</span>Budget Estimate</h2>
<div class="placeholder">
  Budget estimates will be populated once infrastructure sizing and resource planning are complete.
  Preliminary cost modelling is available via the GCP Infrastructure Provisioner module.
</div>

<!-- 10. Recommendation & Next Steps -->
<h2><span class="section-num">10</span>Recommendation &amp; Next Steps</h2>
<ol style="margin:8px 0 8px 24px;font-size:14px;">
  <li>Complete expert review of {needs_review} objects flagged for manual assessment</li>
  <li>Remediate {incompatible} incompatible custom objects using AI-assisted code generation</li>
  <li>Validate integration points in a dedicated sandbox environment</li>
  <li>Finalise infrastructure sizing and GCP provisioning plan</li>
  <li>Establish migration runbook and cutover schedule</li>
  <li>Secure board approval for estimated timeline of {timeline_duration}</li>
</ol>

<div class="footer">
  HanaForge &mdash; AI-Native S/4HANA Migration Platform &bull; Generated {generated}
</div>

</body>
</html>"""

        return html.encode("utf-8")

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
