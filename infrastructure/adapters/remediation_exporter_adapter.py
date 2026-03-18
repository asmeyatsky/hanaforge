"""RemediationExporterAdapter — implements RemediationExporterPort with multi-format export support.

Supports: Jira (JSON), Azure DevOps (CSV), CSV.
"""

from __future__ import annotations

import csv
import io
import json

from domain.entities.custom_object import CustomObject
from domain.entities.remediation import RemediationSuggestion
from domain.ports.remediation_export_ports import RemediationExportFormat

# Effort points -> Jira / Azure DevOps priority mapping (5 = highest priority)
_EFFORT_TO_JIRA_PRIORITY: dict[int, str] = {
    5: "Highest",
    4: "High",
    3: "Medium",
    2: "Low",
    1: "Lowest",
}

_EFFORT_TO_ADO_PRIORITY: dict[int, int] = {
    5: 1,
    4: 1,
    3: 2,
    2: 3,
    1: 4,
}


class RemediationExporterAdapter:
    """Dispatches export to the appropriate format handler."""

    async def export_remediations(
        self,
        remediations: list[RemediationSuggestion],
        objects: list[CustomObject],
        format: RemediationExportFormat,
    ) -> bytes:
        dispatch = {
            RemediationExportFormat.JIRA: self._export_to_jira,
            RemediationExportFormat.AZURE_DEVOPS: self._export_to_azure_devops,
            RemediationExportFormat.CSV: self._export_to_csv,
        }
        handler = dispatch.get(format)
        if handler is None:
            raise ValueError(f"Unsupported export format: {format.value}")
        return handler(remediations, objects)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_object_lookup(objects: list[CustomObject]) -> dict[str, CustomObject]:
        return {obj.id: obj for obj in objects}

    @staticmethod
    def _effort_points_value(obj: CustomObject) -> int:
        """Return the effort points for an object, defaulting to 3 (medium)."""
        return obj.complexity_score.points if obj.complexity_score is not None else 3

    # ------------------------------------------------------------------
    # Jira — JSON format (story / bug structure)
    # ------------------------------------------------------------------

    @classmethod
    def _export_to_jira(
        cls,
        remediations: list[RemediationSuggestion],
        objects: list[CustomObject],
    ) -> bytes:
        obj_lookup = cls._build_object_lookup(objects)
        issues: list[dict] = []

        for r in remediations:
            obj = obj_lookup.get(r.object_id)
            effort = cls._effort_points_value(obj) if obj else 3
            obj_name = obj.object_name if obj else r.object_id
            obj_type = obj.object_type.value if obj else "UNKNOWN"
            domain = obj.domain.value if obj else "UNKNOWN"

            # Use "Bug" for deprecated API issues, "Story" for others
            issue_type = "Bug" if r.deprecated_api else "Story"

            issues.append({
                "fields": {
                    "project": {"key": "HANA"},
                    "issuetype": {"name": issue_type},
                    "summary": f"[{obj_type}] {obj_name}: {r.issue_type}",
                    "description": (
                        f"*Deprecated API:* {r.deprecated_api}\n"
                        f"*Suggested Replacement:* {r.suggested_replacement}\n\n"
                        f"*Generated Code:*\n{{code:java}}\n{r.generated_code}\n{{code}}\n\n"
                        f"*Confidence Score:* {r.confidence_score:.0%}\n"
                        f"*Review Status:* {r.status.value}\n"
                        f"*Business Domain:* {domain}"
                    ),
                    "priority": {"name": _EFFORT_TO_JIRA_PRIORITY.get(effort, "Medium")},
                    "labels": [
                        "hanaforge",
                        f"domain-{domain.lower()}",
                        f"effort-{effort}",
                    ],
                },
                "remediation_id": r.id,
                "object_id": r.object_id,
                "effort_points": effort,
            })

        payload = {"issues": issues}
        return json.dumps(payload, indent=2).encode("utf-8")

    # ------------------------------------------------------------------
    # Azure DevOps — CSV format
    # ------------------------------------------------------------------

    @classmethod
    def _export_to_azure_devops(
        cls,
        remediations: list[RemediationSuggestion],
        objects: list[CustomObject],
    ) -> bytes:
        obj_lookup = cls._build_object_lookup(objects)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Work Item Type", "Title", "Description", "Priority",
            "State", "Tags",
        ])

        for r in remediations:
            obj = obj_lookup.get(r.object_id)
            effort = cls._effort_points_value(obj) if obj else 3
            obj_name = obj.object_name if obj else r.object_id
            obj_type = obj.object_type.value if obj else "UNKNOWN"
            domain = obj.domain.value if obj else "UNKNOWN"

            work_item_type = "Bug" if r.deprecated_api else "User Story"
            title = f"[{obj_type}] {obj_name}: {r.issue_type}"
            description = (
                f"Deprecated API: {r.deprecated_api}\n"
                f"Suggested Replacement: {r.suggested_replacement}\n"
                f"Generated Code:\n{r.generated_code}\n"
                f"Confidence Score: {r.confidence_score:.0%}\n"
                f"Review Status: {r.status.value}\n"
                f"Business Domain: {domain}"
            )
            priority = _EFFORT_TO_ADO_PRIORITY.get(effort, 2)
            state = "New"
            tags = ";".join([
                "hanaforge",
                f"domain-{domain.lower()}",
                f"effort-{effort}",
            ])

            writer.writerow([
                work_item_type, title, description, priority,
                state, tags,
            ])

        return output.getvalue().encode("utf-8")

    # ------------------------------------------------------------------
    # Generic CSV
    # ------------------------------------------------------------------

    @classmethod
    def _export_to_csv(
        cls,
        remediations: list[RemediationSuggestion],
        objects: list[CustomObject],
    ) -> bytes:
        obj_lookup = cls._build_object_lookup(objects)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Remediation ID", "Object ID", "Object Name", "Object Type",
            "Business Domain", "Issue Type", "Deprecated API",
            "Suggested Replacement", "Generated Code", "Confidence Score",
            "Effort Points", "Review Status", "Reviewed By", "Created At",
        ])

        for r in remediations:
            obj = obj_lookup.get(r.object_id)
            effort = cls._effort_points_value(obj) if obj else 3
            obj_name = obj.object_name if obj else r.object_id
            obj_type = obj.object_type.value if obj else "UNKNOWN"
            domain = obj.domain.value if obj else "UNKNOWN"

            writer.writerow([
                r.id,
                r.object_id,
                obj_name,
                obj_type,
                domain,
                r.issue_type,
                r.deprecated_api,
                r.suggested_replacement,
                r.generated_code,
                f"{r.confidence_score:.2f}",
                effort,
                r.status.value,
                r.reviewed_by or "",
                r.created_at.isoformat(),
            ])

        return output.getvalue().encode("utf-8")
