"""Remediation export ports — async boundaries for backlog export to project management tools."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from domain.entities.custom_object import CustomObject
from domain.entities.remediation import RemediationSuggestion


class RemediationExportFormat(Enum):
    JIRA = "JIRA"
    AZURE_DEVOPS = "AZURE_DEVOPS"
    CSV = "CSV"


class RemediationExporterPort(Protocol):
    """Export remediation suggestions to various project management tool formats."""

    async def export_remediations(
        self,
        remediations: list[RemediationSuggestion],
        objects: list[CustomObject],
        format: RemediationExportFormat,
    ) -> bytes: ...
