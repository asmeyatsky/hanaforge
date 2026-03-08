"""Infrastructure ports — async boundaries for GCP provisioning and Terraform generation.

Architectural Intent:
- Protocol-based ports defining the boundary between domain and infrastructure
- TerraformGeneratorPort: generates and validates HCL from domain plans
- ProvisioningPort: applies Terraform via Cloud Build pipeline
- QuickSizerParserPort: parses SAP Quick Sizer XML into domain SizingInput
- InfrastructurePlanRepositoryPort: persistence for InfrastructurePlan aggregates
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.entities.infrastructure_plan import InfrastructurePlan
from domain.value_objects.gcp_types import SizingInput, ValidationResult


@dataclass(frozen=True)
class ProvisioningResult:
    """Result of a Terraform apply operation."""

    success: bool
    plan_ref: str
    outputs: dict[str, str]
    duration_minutes: int
    error_message: str | None = None


class TerraformGeneratorPort(Protocol):
    async def generate_plan(self, plan: InfrastructurePlan) -> str:
        """Generate complete Terraform HCL for an SAP GCP landing zone."""
        ...

    async def validate_plan(self, hcl: str) -> ValidationResult:
        """Validate Terraform HCL syntax and SAP-specific rules."""
        ...


class ProvisioningPort(Protocol):
    async def apply_terraform(self, plan_ref: str) -> ProvisioningResult:
        """Apply Terraform plan via Cloud Build pipeline."""
        ...

    async def get_status(self, plan_ref: str) -> str:
        """Get current provisioning status for a plan reference."""
        ...

    async def destroy(self, plan_ref: str) -> bool:
        """Destroy provisioned infrastructure."""
        ...


class QuickSizerParserPort(Protocol):
    async def parse_quick_sizer_xml(self, xml_bytes: bytes) -> SizingInput:
        """Parse SAP Quick Sizer XML output into a SizingInput value object."""
        ...


class InfrastructurePlanRepositoryPort(Protocol):
    async def save(self, plan: InfrastructurePlan) -> None: ...
    async def get_by_id(self, id: str) -> InfrastructurePlan | None: ...
    async def list_by_programme(self, programme_id: str) -> list[InfrastructurePlan]: ...
    async def get_latest_by_programme(self, programme_id: str) -> InfrastructurePlan | None: ...
