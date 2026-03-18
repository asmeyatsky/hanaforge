"""CloudBuildProvisioningAdapter — provisions SAP infrastructure via GCP Cloud Build.

Implements ProvisioningPort. Generates Cloud Build YAML configurations for
Terraform init/plan/apply/destroy workflows, tracks provisioning status per
plan reference, and returns structured ProvisioningResult objects.

Actual Cloud Build API calls are stubbed for development; the YAML generation
is fully functional and produces production-grade cloudbuild.yaml content.
"""

from __future__ import annotations

import logging
import textwrap
import time
from datetime import datetime, timezone
from enum import Enum

import yaml

from domain.ports.infrastructure_ports import ProvisioningResult

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Status tracking
# ------------------------------------------------------------------


class _ProvisioningStatus(str, Enum):
    """Internal status for tracked provisioning operations."""

    PENDING = "PENDING"
    INITIALIZING = "INITIALIZING"
    PLANNING = "PLANNING"
    APPLYING = "APPLYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DESTROYING = "DESTROYING"
    DESTROYED = "DESTROYED"


# ------------------------------------------------------------------
# Default Terraform image and timeouts
# ------------------------------------------------------------------

_TERRAFORM_IMAGE = "hashicorp/terraform:1.7"
_DEFAULT_TIMEOUT_SECONDS = 3600  # 1 hour
_DESTROY_TIMEOUT_SECONDS = 1800  # 30 minutes


class CloudBuildProvisioningAdapter:
    """Implements ProvisioningPort — orchestrates Terraform via Cloud Build.

    Generates proper Cloud Build YAML configs, tracks provisioning state
    per plan_ref, and returns structured results. Cloud Build API
    submission is stubbed for development but the YAML output is real.
    """

    def __init__(
        self,
        *,
        gcp_project_id: str = "",
        gcp_region: str = "us-central1",
        terraform_state_bucket: str = "",
        service_account: str = "",
        log_bucket: str = "",
    ) -> None:
        self._gcp_project_id = gcp_project_id
        self._gcp_region = gcp_region
        self._terraform_state_bucket = terraform_state_bucket or f"{gcp_project_id}-tfstate"
        self._service_account = service_account
        self._log_bucket = log_bucket or f"{gcp_project_id}-cloudbuild-logs"

        # In-memory status tracking
        self._statuses: dict[str, _ProvisioningStatus] = {}
        self._started_at: dict[str, datetime] = {}
        self._build_configs: dict[str, str] = {}

    # ------------------------------------------------------------------
    # ProvisioningPort implementation
    # ------------------------------------------------------------------

    async def apply_terraform(self, plan_ref: str) -> ProvisioningResult:
        """Apply Terraform plan via Cloud Build pipeline.

        Generates the Cloud Build YAML, stores status, and simulates
        a successful provisioning run. In production this would submit
        the build to the Cloud Build API and poll for completion.
        """
        start = time.monotonic()
        self._statuses[plan_ref] = _ProvisioningStatus.INITIALIZING
        self._started_at[plan_ref] = datetime.now(timezone.utc)

        logger.info("Provisioning started for plan_ref=%s", plan_ref)

        try:
            # Generate the Cloud Build YAML for apply
            build_yaml = self.generate_cloudbuild_yaml(plan_ref, action="apply")
            self._build_configs[plan_ref] = build_yaml

            # Simulate progression through stages
            self._statuses[plan_ref] = _ProvisioningStatus.PLANNING
            logger.info("Terraform plan generated for plan_ref=%s", plan_ref)

            self._statuses[plan_ref] = _ProvisioningStatus.APPLYING
            logger.info("Terraform apply in progress for plan_ref=%s", plan_ref)

            # --- Stub: In production, submit build_yaml to Cloud Build API ---
            # build_id = await self._submit_cloud_build(build_yaml)
            # result = await self._poll_build_status(build_id)
            # ---

            elapsed = time.monotonic() - start
            duration_minutes = max(1, int(elapsed / 60))

            self._statuses[plan_ref] = _ProvisioningStatus.SUCCEEDED
            logger.info(
                "Provisioning succeeded for plan_ref=%s (%.1fs)", plan_ref, elapsed
            )

            return ProvisioningResult(
                success=True,
                plan_ref=plan_ref,
                outputs={
                    "project_id": self._gcp_project_id,
                    "region": self._gcp_region,
                    "vpc_network": f"sap-vpc-{plan_ref[:8]}",
                    "hana_instance": f"sap-hana-{plan_ref[:8]}",
                    "app_instance_group": f"sap-app-mig-{plan_ref[:8]}",
                    "cloud_build_config": "cloudbuild.yaml generated",
                    "terraform_state_bucket": self._terraform_state_bucket,
                },
                duration_minutes=duration_minutes,
            )

        except Exception as exc:
            self._statuses[plan_ref] = _ProvisioningStatus.FAILED
            logger.error(
                "Provisioning failed for plan_ref=%s: %s", plan_ref, exc
            )
            elapsed = time.monotonic() - start
            return ProvisioningResult(
                success=False,
                plan_ref=plan_ref,
                outputs={},
                duration_minutes=max(1, int(elapsed / 60)),
                error_message=str(exc),
            )

    async def get_status(self, plan_ref: str) -> str:
        """Get current provisioning status for a plan reference."""
        status = self._statuses.get(plan_ref, _ProvisioningStatus.PENDING)
        return status.value

    async def destroy(self, plan_ref: str) -> bool:
        """Destroy provisioned infrastructure via Cloud Build.

        Generates a Cloud Build YAML for terraform destroy and simulates
        execution. Returns True on success.
        """
        logger.info("Destroy requested for plan_ref=%s", plan_ref)
        self._statuses[plan_ref] = _ProvisioningStatus.DESTROYING

        try:
            destroy_yaml = self.generate_cloudbuild_yaml(plan_ref, action="destroy")
            self._build_configs[f"{plan_ref}_destroy"] = destroy_yaml

            # --- Stub: In production, submit to Cloud Build API ---
            # build_id = await self._submit_cloud_build(destroy_yaml)
            # await self._poll_build_status(build_id)
            # ---

            self._statuses[plan_ref] = _ProvisioningStatus.DESTROYED
            logger.info("Infrastructure destroyed for plan_ref=%s", plan_ref)
            return True

        except Exception as exc:
            self._statuses[plan_ref] = _ProvisioningStatus.FAILED
            logger.error("Destroy failed for plan_ref=%s: %s", plan_ref, exc)
            return False

    # ------------------------------------------------------------------
    # Cloud Build YAML generation
    # ------------------------------------------------------------------

    def generate_cloudbuild_yaml(self, plan_ref: str, action: str = "apply") -> str:
        """Generate a GCP Cloud Build YAML configuration for Terraform.

        Args:
            plan_ref: Unique identifier for the infrastructure plan.
            action: One of 'apply' or 'destroy'.

        Returns:
            A valid Cloud Build YAML string with Terraform steps,
            substitution variables, service account config, logging,
            and timeout settings.
        """
        substitutions = {
            "_PROJECT_ID": self._gcp_project_id or "${PROJECT_ID}",
            "_REGION": self._gcp_region,
            "_PLAN_REF": plan_ref,
            "_TF_STATE_BUCKET": self._terraform_state_bucket,
        }

        # Common init step
        init_step = {
            "id": "terraform-init",
            "name": _TERRAFORM_IMAGE,
            "entrypoint": "sh",
            "args": [
                "-c",
                textwrap.dedent("""\
                    terraform init \
                      -backend-config="bucket=$_TF_STATE_BUCKET" \
                      -backend-config="prefix=hanaforge/$_PLAN_REF" \
                      -no-color"""),
            ],
            "dir": "terraform",
        }

        if action == "destroy":
            steps = [
                init_step,
                {
                    "id": "terraform-plan-destroy",
                    "name": _TERRAFORM_IMAGE,
                    "entrypoint": "sh",
                    "args": [
                        "-c",
                        textwrap.dedent("""\
                            terraform plan -destroy \
                              -var="project_id=$_PROJECT_ID" \
                              -var="region=$_REGION" \
                              -out=destroy.tfplan \
                              -no-color"""),
                    ],
                    "dir": "terraform",
                    "waitFor": ["terraform-init"],
                },
                {
                    "id": "terraform-destroy",
                    "name": _TERRAFORM_IMAGE,
                    "entrypoint": "sh",
                    "args": [
                        "-c",
                        "terraform apply -auto-approve destroy.tfplan -no-color",
                    ],
                    "dir": "terraform",
                    "waitFor": ["terraform-plan-destroy"],
                },
            ]
            timeout_seconds = _DESTROY_TIMEOUT_SECONDS
        else:
            # Default: apply
            steps = [
                init_step,
                {
                    "id": "terraform-plan",
                    "name": _TERRAFORM_IMAGE,
                    "entrypoint": "sh",
                    "args": [
                        "-c",
                        textwrap.dedent("""\
                            terraform plan \
                              -var="project_id=$_PROJECT_ID" \
                              -var="region=$_REGION" \
                              -out=apply.tfplan \
                              -no-color"""),
                    ],
                    "dir": "terraform",
                    "waitFor": ["terraform-init"],
                },
                {
                    "id": "terraform-apply",
                    "name": _TERRAFORM_IMAGE,
                    "entrypoint": "sh",
                    "args": [
                        "-c",
                        "terraform apply -auto-approve apply.tfplan -no-color",
                    ],
                    "dir": "terraform",
                    "waitFor": ["terraform-plan"],
                },
            ]
            timeout_seconds = _DEFAULT_TIMEOUT_SECONDS

        build_config: dict = {
            "steps": steps,
            "substitutions": substitutions,
            "options": {
                "logging": "GCS_ONLY" if self._log_bucket else "CLOUD_LOGGING_ONLY",
                "logsBucket": f"gs://{self._log_bucket}" if self._log_bucket else "",
                "machineType": "E2_HIGHCPU_8",
            },
            "timeout": f"{timeout_seconds}s",
            "tags": [
                "hanaforge",
                f"plan-{plan_ref[:8]}",
                f"action-{action}",
            ],
        }

        # Add service account if configured
        if self._service_account:
            build_config["serviceAccount"] = (
                f"projects/{self._gcp_project_id}/serviceAccounts/{self._service_account}"
            )

        # Remove empty logsBucket to keep YAML clean
        if not build_config["options"]["logsBucket"]:
            del build_config["options"]["logsBucket"]

        return yaml.dump(build_config, default_flow_style=False, sort_keys=False)
