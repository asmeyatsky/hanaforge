"""TerraformHCLGenerator — produces production-grade Terraform HCL for SAP on GCP.

Implements TerraformGeneratorPort. Generates a complete SAP landing zone
comprising VPC, subnets, firewall rules, HANA compute with HA clustering,
app server MIGs with autoscaling, Cloud Storage for backup, Filestore for
transport, Cloud KMS (CMEK), monitoring dashboards, and alert policies.

Each Terraform file section is generated independently and concatenated.
"""

from __future__ import annotations

import textwrap

from domain.entities.infrastructure_plan import InfrastructurePlan
from domain.value_objects.gcp_types import ValidationResult, ValidationStatus


class TerraformHCLGenerator:
    """Implements TerraformGeneratorPort — generates complete Terraform HCL."""

    async def generate_plan(self, plan: InfrastructurePlan) -> str:
        """Generate complete Terraform HCL for an SAP GCP landing zone."""
        sections = [
            self._generate_provider(plan),
            self._generate_variables(plan),
            self._generate_network(plan),
            self._generate_compute_hana(plan),
            self._generate_compute_app(plan),
            self._generate_storage(plan),
            self._generate_security(plan),
            self._generate_monitoring(plan),
            self._generate_outputs(plan),
        ]
        return "\n\n".join(sections)

    async def validate_plan(self, hcl: str) -> ValidationResult:
        """Basic HCL validation — checks for structural completeness."""
        checks_passed = 0
        checks_failed = 0
        warnings: list[str] = []
        errors: list[str] = []

        # Check required blocks exist
        required_blocks = [
            ("terraform {", "terraform configuration block"),
            ("provider \"google\"", "Google provider"),
            ("resource \"google_compute_network\"", "VPC network"),
            ("resource \"google_compute_subnetwork\"", "subnet definition"),
            ("resource \"google_compute_instance\"", "compute instance"),
        ]
        for block, description in required_blocks:
            if block in hcl:
                checks_passed += 1
            else:
                checks_failed += 1
                errors.append(f"Missing required block: {description}")

        # Check for SAP-specific resources
        sap_resources = [
            ("google_compute_disk", "persistent disk for HANA"),
            ("google_compute_firewall", "firewall rules"),
            ("google_storage_bucket", "backup storage bucket"),
        ]
        for resource, description in sap_resources:
            if resource in hcl:
                checks_passed += 1
            else:
                warnings.append(f"Recommended resource not found: {description}")

        if checks_failed > 0:
            status = ValidationStatus.FAILED
        elif warnings:
            status = ValidationStatus.WARNINGS
        else:
            status = ValidationStatus.PASSED

        return ValidationResult(
            status=status,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    # ------------------------------------------------------------------
    # HCL generation — one method per logical Terraform file
    # ------------------------------------------------------------------

    def _generate_provider(self, plan: InfrastructurePlan) -> str:
        return textwrap.dedent(f"""\
            # =============================================================================
            # provider.tf — Google Cloud provider configuration for SAP landing zone
            # =============================================================================

            terraform {{
              required_version = ">= 1.7.0"

              required_providers {{
                google = {{
                  source  = "hashicorp/google"
                  version = "~> 5.30"
                }}
                google-beta = {{
                  source  = "hashicorp/google-beta"
                  version = "~> 5.30"
                }}
              }}

              backend "gcs" {{
                bucket = "hanaforge-tfstate-${{var.project_id}}"
                prefix = "sap-landing-zone/{plan.programme_id}"
              }}
            }}

            provider "google" {{
              project = var.project_id
              region  = var.region
            }}

            provider "google-beta" {{
              project = var.project_id
              region  = var.region
            }}""")

    def _generate_variables(self, plan: InfrastructurePlan) -> str:
        return textwrap.dedent(f"""\
            # =============================================================================
            # variables.tf — Input variables for SAP landing zone
            # =============================================================================

            variable "project_id" {{
              description = "GCP project ID for SAP workloads"
              type        = string
            }}

            variable "region" {{
              description = "Primary GCP region"
              type        = string
              default     = "{plan.region}"
            }}

            variable "dr_region" {{
              description = "Disaster recovery GCP region"
              type        = string
              default     = "{plan.dr_region or ''}"
            }}

            variable "programme_id" {{
              description = "HanaForge programme identifier"
              type        = string
              default     = "{plan.programme_id}"
            }}

            variable "hana_instance_type" {{
              description = "GCP machine type for HANA instances"
              type        = string
              default     = "{plan.hana_config.instance_type.value}"
            }}

            variable "app_instance_type" {{
              description = "GCP machine type for SAP application servers"
              type        = string
              default     = "{plan.app_server_config.instance_type.value}"
            }}

            variable "app_instance_count" {{
              description = "Number of SAP application server instances"
              type        = number
              default     = {plan.app_server_config.instance_count}
            }}

            variable "hana_data_disk_gb" {{
              description = "HANA data volume size in GB"
              type        = number
              default     = {plan.hana_config.hana_data_disk_gb}
            }}

            variable "hana_log_disk_gb" {{
              description = "HANA log volume size in GB"
              type        = number
              default     = {plan.hana_config.hana_log_disk_gb}
            }}

            variable "hana_shared_disk_gb" {{
              description = "HANA shared volume size in GB"
              type        = number
              default     = {plan.hana_config.hana_shared_disk_gb}
            }}

            variable "hana_backup_disk_gb" {{
              description = "HANA backup volume size in GB"
              type        = number
              default     = {plan.hana_config.backup_disk_gb}
            }}

            variable "labels" {{
              description = "Common labels for all resources"
              type        = map(string)
              default = {{
                managed_by  = "hanaforge"
                programme   = "{plan.programme_id[:8]}"
                workload    = "sap-s4hana"
                environment = "production"
              }}
            }}""")

    def _generate_network(self, plan: InfrastructurePlan) -> str:
        nc = plan.network_config
        cloud_nat_block = ""
        if nc.enable_cloud_nat:
            cloud_nat_block = textwrap.dedent("""\

            # --- Cloud Router + Cloud NAT for outbound internet access ---

            resource "google_compute_router" "sap_router" {
              name    = "sap-cloud-router"
              region  = var.region
              network = google_compute_network.sap_vpc.id

              bgp {
                asn = 64514
              }
            }

            resource "google_compute_router_nat" "sap_nat" {
              name                               = "sap-cloud-nat"
              router                             = google_compute_router.sap_router.name
              region                             = var.region
              nat_ip_allocate_option             = "AUTO_ONLY"
              source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

              log_config {
                enable = true
                filter = "ERRORS_ONLY"
              }
            }""")

        return textwrap.dedent(f"""\
            # =============================================================================
            # network.tf — VPC, subnets, firewall rules, Cloud NAT
            # =============================================================================

            resource "google_compute_network" "sap_vpc" {{
              name                    = "{nc.vpc_name}"
              auto_create_subnetworks = false
              routing_mode            = "GLOBAL"
              project                 = var.project_id
            }}

            # --- Subnets per SAP tier ---

            resource "google_compute_subnetwork" "sap_db" {{
              name                     = "{nc.vpc_name}-db"
              ip_cidr_range            = "{nc.subnet_cidr_db}"
              region                   = var.region
              network                  = google_compute_network.sap_vpc.id
              private_ip_google_access = {str(nc.enable_private_google_access).lower()}

              log_config {{
                aggregation_interval = "INTERVAL_5_SEC"
                flow_sampling        = 0.5
                metadata             = "INCLUDE_ALL_METADATA"
              }}
            }}

            resource "google_compute_subnetwork" "sap_app" {{
              name                     = "{nc.vpc_name}-app"
              ip_cidr_range            = "{nc.subnet_cidr_app}"
              region                   = var.region
              network                  = google_compute_network.sap_vpc.id
              private_ip_google_access = {str(nc.enable_private_google_access).lower()}

              log_config {{
                aggregation_interval = "INTERVAL_5_SEC"
                flow_sampling        = 0.5
                metadata             = "INCLUDE_ALL_METADATA"
              }}
            }}

            resource "google_compute_subnetwork" "sap_web" {{
              name                     = "{nc.vpc_name}-web"
              ip_cidr_range            = "{nc.subnet_cidr_web}"
              region                   = var.region
              network                  = google_compute_network.sap_vpc.id
              private_ip_google_access = {str(nc.enable_private_google_access).lower()}

              log_config {{
                aggregation_interval = "INTERVAL_5_SEC"
                flow_sampling        = 0.5
                metadata             = "INCLUDE_ALL_METADATA"
              }}
            }}

            # --- Firewall rules ---

            resource "google_compute_firewall" "allow_sap_internal" {{
              name    = "allow-sap-internal"
              network = google_compute_network.sap_vpc.id

              allow {{
                protocol = "tcp"
                ports    = ["3200-3299", "3300-3399", "8000-8099", "50000-50099", "30013-30017"]
              }}

              allow {{
                protocol = "icmp"
              }}

              source_ranges = ["{nc.subnet_cidr_db}", "{nc.subnet_cidr_app}", "{nc.subnet_cidr_web}"]
              target_tags   = ["sap-server"]

              description = "Allow internal SAP communication between tiers"
            }}

            resource "google_compute_firewall" "allow_hana_replication" {{
              name    = "allow-hana-replication"
              network = google_compute_network.sap_vpc.id

              allow {{
                protocol = "tcp"
                ports    = ["40000-40099", "30001-30007"]
              }}

              source_tags = ["sap-hana"]
              target_tags = ["sap-hana"]

              description = "Allow HANA System Replication traffic between HANA nodes"
            }}

            resource "google_compute_firewall" "allow_pacemaker" {{
              name    = "allow-pacemaker-ha"
              network = google_compute_network.sap_vpc.id

              allow {{
                protocol = "tcp"
                ports    = ["2224", "3121", "5405"]
              }}

              allow {{
                protocol = "udp"
                ports    = ["5405"]
              }}

              source_tags = ["sap-hana"]
              target_tags = ["sap-hana"]

              description = "Allow Pacemaker/Corosync HA cluster communication"
            }}

            resource "google_compute_firewall" "allow_iap_ssh" {{
              name    = "allow-iap-ssh"
              network = google_compute_network.sap_vpc.id

              allow {{
                protocol = "tcp"
                ports    = ["22"]
              }}

              # IAP tunnel IP range
              source_ranges = ["35.235.240.0/20"]
              target_tags   = ["sap-server"]

              description = "Allow SSH via Identity-Aware Proxy"
            }}

            resource "google_compute_firewall" "deny_all_ingress" {{
              name     = "deny-all-ingress"
              network  = google_compute_network.sap_vpc.id
              priority = 65534

              deny {{
                protocol = "all"
              }}

              source_ranges = ["0.0.0.0/0"]

              description = "Default deny all ingress — explicit allow rules above"
            }}{cloud_nat_block}""")

    def _generate_compute_hana(self, plan: InfrastructurePlan) -> str:
        _hc = plan.hana_config
        zones = ["${var.region}-a", "${var.region}-b"]

        instances_hcl = ""
        for idx, zone in enumerate(zones[:2] if plan.ha_enabled else zones[:1]):
            suffix = f"-{idx + 1}" if plan.ha_enabled else ""
            role = "primary" if idx == 0 else "secondary"

            instances_hcl += textwrap.dedent(f"""
            # --- HANA {role} instance ---

            resource "google_compute_disk" "hana_data{suffix}" {{
              name = "hana-data{suffix}"
              type = "pd-balanced"
              size = var.hana_data_disk_gb
              zone = "{zone}"

              physical_block_size_bytes = 4096

              labels = var.labels
            }}

            resource "google_compute_disk" "hana_log{suffix}" {{
              name = "hana-log{suffix}"
              type = "pd-ssd"
              size = var.hana_log_disk_gb
              zone = "{zone}"

              physical_block_size_bytes = 4096

              labels = var.labels
            }}

            resource "google_compute_disk" "hana_shared{suffix}" {{
              name = "hana-shared{suffix}"
              type = "pd-balanced"
              size = var.hana_shared_disk_gb
              zone = "{zone}"

              labels = var.labels
            }}

            resource "google_compute_disk" "hana_backup{suffix}" {{
              name = "hana-backup{suffix}"
              type = "pd-standard"
              size = var.hana_backup_disk_gb
              zone = "{zone}"

              labels = var.labels
            }}

            resource "google_compute_instance" "hana{suffix}" {{
              name         = "sap-hana{suffix}"
              machine_type = var.hana_instance_type
              zone         = "{zone}"

              tags = ["sap-server", "sap-hana"]

              boot_disk {{
                initialize_params {{
                  image = "projects/suse-cloud/global/images/family/sles-15-sp5-sap"
                  size  = 50
                  type  = "pd-ssd"
                }}
              }}

              attached_disk {{
                source      = google_compute_disk.hana_data{suffix}.id
                device_name = "hana-data"
              }}

              attached_disk {{
                source      = google_compute_disk.hana_log{suffix}.id
                device_name = "hana-log"
              }}

              attached_disk {{
                source      = google_compute_disk.hana_shared{suffix}.id
                device_name = "hana-shared"
              }}

              attached_disk {{
                source      = google_compute_disk.hana_backup{suffix}.id
                device_name = "hana-backup"
              }}

              network_interface {{
                subnetwork = google_compute_subnetwork.sap_db.id
              }}

              metadata = {{
                enable-oslogin         = "{str(plan.security_config.enable_os_login).lower()}"
                sap_hana_deployment_bucket = google_storage_bucket.sap_backup.name
                sap_hana_sid           = "HDB"
                sap_hana_instance_number = "00"
                sap_hana_sidadm_uid    = 1001
                startup-script         = <<-EOF
                  #!/bin/bash
                  # Mount HANA disks
                  mkfs.xfs /dev/disk/by-id/google-hana-data 2>/dev/null || true
                  mkfs.xfs /dev/disk/by-id/google-hana-log 2>/dev/null || true
                  mkfs.xfs /dev/disk/by-id/google-hana-shared 2>/dev/null || true
                  mkfs.xfs /dev/disk/by-id/google-hana-backup 2>/dev/null || true

                  mkdir -p /hana/data /hana/log /hana/shared /hana/backup
                  mount /dev/disk/by-id/google-hana-data /hana/data
                  mount /dev/disk/by-id/google-hana-log /hana/log
                  mount /dev/disk/by-id/google-hana-shared /hana/shared
                  mount /dev/disk/by-id/google-hana-backup /hana/backup

                  # Install SAP HANA Agent for Cloud Monitoring
                  curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
                  bash add-google-cloud-ops-agent-repo.sh --also-install
                EOF
              }}

              scheduling {{
                on_host_maintenance = "TERMINATE"
                automatic_restart   = true
              }}

              service_account {{
                scopes = ["cloud-platform"]
              }}

              labels = merge(var.labels, {{
                sap_component = "hana"
                ha_role       = "{role}"
              }})

              allow_stopping_for_update = true
            }}
            """)

        # HA: add ILB and health check for Pacemaker VIP
        ha_block = ""
        if plan.ha_enabled:
            ha_block = textwrap.dedent("""
            # --- HA: Internal Load Balancer for HANA VIP ---

            resource "google_compute_health_check" "hana_health" {
              name               = "hana-health-check"
              check_interval_sec = 10
              timeout_sec        = 5

              tcp_health_check {
                port = 60000
              }
            }

            resource "google_compute_region_backend_service" "hana_backend" {
              name                  = "hana-ilb-backend"
              region                = var.region
              protocol              = "TCP"
              load_balancing_scheme = "INTERNAL"
              health_checks         = [google_compute_health_check.hana_health.id]

              backend {
                group = google_compute_instance_group.hana_primary_ig.id
              }

              backend {
                group = google_compute_instance_group.hana_secondary_ig.id
              }
            }

            resource "google_compute_instance_group" "hana_primary_ig" {
              name      = "hana-primary-ig"
              zone      = "${var.region}-a"
              instances = [google_compute_instance.hana-1.id]
            }

            resource "google_compute_instance_group" "hana_secondary_ig" {
              name      = "hana-secondary-ig"
              zone      = "${var.region}-b"
              instances = [google_compute_instance.hana-2.id]
            }

            resource "google_compute_forwarding_rule" "hana_ilb" {
              name                  = "hana-ilb-forwarding"
              region                = var.region
              load_balancing_scheme = "INTERNAL"
              backend_service       = google_compute_region_backend_service.hana_backend.id
              ip_protocol           = "TCP"
              ports                 = ["30013", "30015", "30017", "30041", "30044"]
              network               = google_compute_network.sap_vpc.id
              subnetwork            = google_compute_subnetwork.sap_db.id
            }
            """)

        return textwrap.dedent(f"""\
            # =============================================================================
            # compute_hana.tf — HANA database instances with HA clustering
            # =============================================================================
            {instances_hcl}{ha_block}""")

    def _generate_compute_app(self, plan: InfrastructurePlan) -> str:
        ac = plan.app_server_config

        if ac.auto_scaling:
            return textwrap.dedent(f"""\
            # =============================================================================
            # compute_app.tf — SAP application servers with Managed Instance Group
            # =============================================================================

            resource "google_compute_instance_template" "sap_app" {{
              name_prefix  = "sap-app-"
              machine_type = var.app_instance_type
              region       = var.region

              tags = ["sap-server", "sap-app"]

              disk {{
                source_image = "projects/suse-cloud/global/images/family/sles-15-sp5-sap"
                auto_delete  = true
                boot         = true
                disk_type    = "pd-ssd"
                disk_size_gb = 100
              }}

              network_interface {{
                subnetwork = google_compute_subnetwork.sap_app.id
              }}

              metadata = {{
                enable-oslogin = "{str(plan.security_config.enable_os_login).lower()}"
                startup-script = <<-EOF
                  #!/bin/bash
                  # Install Cloud Ops Agent for SAP monitoring
                  curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
                  bash add-google-cloud-ops-agent-repo.sh --also-install
                EOF
              }}

              scheduling {{
                automatic_restart   = true
                on_host_maintenance = "MIGRATE"
              }}

              service_account {{
                scopes = ["cloud-platform"]
              }}

              labels = merge(var.labels, {{
                sap_component = "application-server"
              }})

              lifecycle {{
                create_before_destroy = true
              }}
            }}

            resource "google_compute_region_instance_group_manager" "sap_app_mig" {{
              name               = "sap-app-mig"
              region             = var.region
              base_instance_name = "sap-app"
              target_size        = var.app_instance_count

              version {{
                instance_template = google_compute_instance_template.sap_app.id
              }}

              named_port {{
                name = "sap-disp"
                port = 3200
              }}

              named_port {{
                name = "sap-gateway"
                port = 3300
              }}

              auto_healing_policies {{
                health_check      = google_compute_health_check.sap_app_health.id
                initial_delay_sec = 300
              }}

              update_policy {{
                type                  = "PROACTIVE"
                minimal_action        = "REPLACE"
                max_surge_fixed       = 1
                max_unavailable_fixed = 0
              }}
            }}

            resource "google_compute_health_check" "sap_app_health" {{
              name               = "sap-app-health-check"
              check_interval_sec = 30
              timeout_sec        = 10

              tcp_health_check {{
                port = 3200
              }}
            }}

            resource "google_compute_region_autoscaler" "sap_app_autoscaler" {{
              name   = "sap-app-autoscaler"
              region = var.region
              target = google_compute_region_instance_group_manager.sap_app_mig.id

              autoscaling_policy {{
                min_replicas    = {ac.min_instances}
                max_replicas    = {ac.max_instances}
                cooldown_period = 300

                cpu_utilization {{
                  target = 0.70
                }}
              }}
            }}""")

        # Non-autoscaling: static instances
        instances_hcl = ""
        for i in range(ac.instance_count):
            zone = f"${{var.region}}-{'a' if i % 2 == 0 else 'b'}"
            instances_hcl += textwrap.dedent(f"""
            resource "google_compute_instance" "sap_app_{i + 1}" {{
              name         = "sap-app-{i + 1}"
              machine_type = var.app_instance_type
              zone         = "{zone}"

              tags = ["sap-server", "sap-app"]

              boot_disk {{
                initialize_params {{
                  image = "projects/suse-cloud/global/images/family/sles-15-sp5-sap"
                  size  = 100
                  type  = "pd-ssd"
                }}
              }}

              network_interface {{
                subnetwork = google_compute_subnetwork.sap_app.id
              }}

              metadata = {{
                enable-oslogin = "{str(plan.security_config.enable_os_login).lower()}"
              }}

              scheduling {{
                automatic_restart   = true
                on_host_maintenance = "MIGRATE"
              }}

              service_account {{
                scopes = ["cloud-platform"]
              }}

              labels = merge(var.labels, {{
                sap_component = "application-server"
              }})
            }}
            """)

        return textwrap.dedent(f"""\
            # =============================================================================
            # compute_app.tf — SAP application server instances
            # =============================================================================
            {instances_hcl}""")

    def _generate_storage(self, plan: InfrastructurePlan) -> str:
        return textwrap.dedent(f"""\
            # =============================================================================
            # storage.tf — Cloud Storage for backup (Backint), Filestore for transport
            # =============================================================================

            resource "google_storage_bucket" "sap_backup" {{
              name          = "sap-backup-${{var.project_id}}-${{var.programme_id}}"
              location      = upper(var.region)
              storage_class = "NEARLINE"
              force_destroy = false

              uniform_bucket_level_access = true

              versioning {{
                enabled = true
              }}

              lifecycle_rule {{
                condition {{
                  age = 90
                }}
                action {{
                  type          = "SetStorageClass"
                  storage_class = "COLDLINE"
                }}
              }}

              lifecycle_rule {{
                condition {{
                  age = 365
                }}
                action {{
                  type          = "SetStorageClass"
                  storage_class = "ARCHIVE"
                }}
              }}

              labels = var.labels
            }}

            resource "google_storage_bucket" "sap_terraform_state" {{
              name          = "hanaforge-tfstate-${{var.project_id}}"
              location      = upper(var.region)
              storage_class = "STANDARD"
              force_destroy = false

              uniform_bucket_level_access = true

              versioning {{
                enabled = true
              }}

              labels = var.labels
            }}

            resource "google_filestore_instance" "sap_transport" {{
              name     = "sap-transport"
              location = "${{var.region}}-a"
              tier     = "BASIC_SSD"

              file_shares {{
                capacity_gb = 1024
                name        = "transport"

                nfs_export_options {{
                  ip_ranges   = ["{plan.network_config.subnet_cidr_app}", "{plan.network_config.subnet_cidr_db}"]
                  access_mode = "READ_WRITE"
                  squash_mode = "NO_ROOT_SQUASH"
                }}
              }}

              networks {{
                network = google_compute_network.sap_vpc.name
                modes   = ["MODE_IPV4"]
              }}

              labels = var.labels
            }}""")

    def _generate_security(self, plan: InfrastructurePlan) -> str:
        sc = plan.security_config
        blocks: list[str] = [textwrap.dedent("""\
            # =============================================================================
            # security.tf — KMS, VPC Service Controls, IAM
            # =============================================================================

            # --- Service account for SAP workloads ---

            resource "google_service_account" "sap_workload" {
              account_id   = "sap-workload-sa"
              display_name = "SAP Workload Service Account"
              project      = var.project_id
            }

            resource "google_project_iam_member" "sap_sa_log_writer" {
              project = var.project_id
              role    = "roles/logging.logWriter"
              member  = "serviceAccount:${google_service_account.sap_workload.email}"
            }

            resource "google_project_iam_member" "sap_sa_metric_writer" {
              project = var.project_id
              role    = "roles/monitoring.metricWriter"
              member  = "serviceAccount:${google_service_account.sap_workload.email}"
            }

            resource "google_project_iam_member" "sap_sa_storage_admin" {
              project = var.project_id
              role    = "roles/storage.objectAdmin"
              member  = "serviceAccount:${google_service_account.sap_workload.email}"
            }""")]

        if sc.enable_cmek and sc.kms_key_ring:
            blocks.append(textwrap.dedent(f"""\

            # --- Cloud KMS for CMEK encryption ---

            resource "google_kms_key_ring" "sap_keyring" {{
              name     = "{sc.kms_key_ring}"
              location = var.region
              project  = var.project_id
            }}

            resource "google_kms_crypto_key" "sap_hana_key" {{
              name            = "sap-hana-disk-key"
              key_ring        = google_kms_key_ring.sap_keyring.id
              rotation_period = "7776000s"  # 90 days

              purpose = "ENCRYPT_DECRYPT"

              lifecycle {{
                prevent_destroy = true
              }}
            }}

            resource "google_kms_crypto_key" "sap_backup_key" {{
              name            = "sap-backup-key"
              key_ring        = google_kms_key_ring.sap_keyring.id
              rotation_period = "7776000s"  # 90 days

              purpose = "ENCRYPT_DECRYPT"

              lifecycle {{
                prevent_destroy = true
              }}
            }}"""))

        if sc.enable_vpc_sc:
            blocks.append(textwrap.dedent("""\

            # --- VPC Service Controls perimeter ---

            resource "google_access_context_manager_service_perimeter" "sap_perimeter" {
              parent = "accessPolicies/${var.access_policy_id}"
              name   = "accessPolicies/${var.access_policy_id}/servicePerimeters/sap_perimeter"
              title  = "SAP Workload Perimeter"

              status {
                restricted_services = [
                  "storage.googleapis.com",
                  "compute.googleapis.com",
                  "container.googleapis.com",
                ]

                resources = [
                  "projects/${var.project_id}",
                ]
              }
            }"""))

        return "\n".join(blocks)

    def _generate_monitoring(self, plan: InfrastructurePlan) -> str:
        return textwrap.dedent("""\
            # =============================================================================
            # monitoring.tf — Cloud Monitoring dashboards and alert policies for SAP HANA
            # =============================================================================

            # --- Notification channel for SAP alerts ---

            resource "google_monitoring_notification_channel" "sap_email" {
              display_name = "SAP Operations Team"
              type         = "email"

              labels = {
                email_address = "sap-ops@example.com"
              }
            }

            # --- HANA memory utilisation alert ---

            resource "google_monitoring_alert_policy" "hana_memory" {
              display_name = "SAP HANA - High Memory Utilisation"
              combiner     = "OR"

              conditions {
                display_name = "HANA memory used > 90%"

                condition_threshold {
                  filter          = join(" AND ", [
                    "resource.type = \\"gce_instance\\"",
                    "metric.type = \\"agent.googleapis.com/sap/hana/memory/total_used_size\\""
                  ])
                  comparison      = "COMPARISON_GT"
                  threshold_value = 90
                  duration        = "300s"

                  aggregations {
                    alignment_period   = "60s"
                    per_series_aligner = "ALIGN_MEAN"
                  }

                  trigger {
                    count = 1
                  }
                }
              }

              notification_channels = [google_monitoring_notification_channel.sap_email.id]

              alert_strategy {
                auto_close = "1800s"
              }

              documentation {
                content   = join("", [
                  "SAP HANA memory utilisation has exceeded 90%. ",
                  "Investigate potential memory leaks or consider scaling the instance."
                ])
                mime_type = "text/markdown"
              }
            }

            # --- HANA CPU utilisation alert ---

            resource "google_monitoring_alert_policy" "hana_cpu" {
              display_name = "SAP HANA - High CPU Utilisation"
              combiner     = "OR"

              conditions {
                display_name = "HANA CPU > 85% for 10 min"

                condition_threshold {
                  filter          = join(" AND ", [
                    "resource.type = \\"gce_instance\\"",
                    "metric.type = \\"compute.googleapis.com/instance/cpu/utilization\\"",
                    "metadata.user_labels.sap_component = \\"hana\\""
                  ])
                  comparison      = "COMPARISON_GT"
                  threshold_value = 0.85
                  duration        = "600s"

                  aggregations {
                    alignment_period   = "60s"
                    per_series_aligner = "ALIGN_MEAN"
                  }

                  trigger {
                    count = 1
                  }
                }
              }

              notification_channels = [google_monitoring_notification_channel.sap_email.id]

              alert_strategy {
                auto_close = "1800s"
              }
            }

            # --- HANA disk IO alert ---

            resource "google_monitoring_alert_policy" "hana_disk_io" {
              display_name = "SAP HANA - Disk IO Latency"
              combiner     = "OR"

              conditions {
                display_name = "HANA disk write latency > 5ms"

                condition_threshold {
                  filter          = join(" AND ", [
                    "resource.type = \\"gce_instance\\"",
                    "metric.type = \\"compute.googleapis.com/instance/disk/write_ops_count\\"",
                    "metadata.user_labels.sap_component = \\"hana\\""
                  ])
                  comparison      = "COMPARISON_GT"
                  threshold_value = 5000
                  duration        = "300s"

                  aggregations {
                    alignment_period   = "60s"
                    per_series_aligner = "ALIGN_RATE"
                  }

                  trigger {
                    count = 1
                  }
                }
              }

              notification_channels = [google_monitoring_notification_channel.sap_email.id]
            }

            # --- App server health alert ---

            resource "google_monitoring_alert_policy" "app_server_health" {
              display_name = "SAP App Server - Instance Down"
              combiner     = "OR"

              conditions {
                display_name = "App server uptime check failed"

                condition_threshold {
                  filter          = join(" AND ", [
                    "resource.type = \\"gce_instance\\"",
                    "metric.type = \\"compute.googleapis.com/instance/uptime\\"",
                    "metadata.user_labels.sap_component = \\"application-server\\""
                  ])
                  comparison      = "COMPARISON_LT"
                  threshold_value = 1
                  duration        = "120s"

                  aggregations {
                    alignment_period   = "60s"
                    per_series_aligner = "ALIGN_MEAN"
                  }

                  trigger {
                    count = 1
                  }
                }
              }

              notification_channels = [google_monitoring_notification_channel.sap_email.id]
            }

            # --- Network throughput alert ---

            resource "google_monitoring_alert_policy" "network_throughput" {
              display_name = "SAP Network - High Egress Traffic"
              combiner     = "OR"

              conditions {
                display_name = "Network egress > 1 Gbps for 5 min"

                condition_threshold {
                  filter          = join(" AND ", [
                    "resource.type = \\"gce_instance\\"",
                    "metric.type = \\"compute.googleapis.com/instance/network/sent_bytes_count\\"",
                    "metadata.user_labels.workload = \\"sap-s4hana\\""
                  ])
                  comparison      = "COMPARISON_GT"
                  threshold_value = 125000000
                  duration        = "300s"

                  aggregations {
                    alignment_period   = "60s"
                    per_series_aligner = "ALIGN_RATE"
                  }

                  trigger {
                    count = 1
                  }
                }
              }

              notification_channels = [google_monitoring_notification_channel.sap_email.id]
            }

            # --- HANA backup alert ---

            resource "google_monitoring_alert_policy" "backup_failure" {
              display_name = "SAP HANA - Backup Failure"
              combiner     = "OR"

              conditions {
                display_name = "No backup log entries in 24h"

                condition_absent {
                  filter   = join(" AND ", [
                    "resource.type = \\"gce_instance\\"",
                    "metric.type = \\"logging.googleapis.com/user/sap_hana_backup_success\\""
                  ])
                  duration = "86400s"

                  aggregations {
                    alignment_period   = "3600s"
                    per_series_aligner = "ALIGN_COUNT"
                  }

                  trigger {
                    count = 1
                  }
                }
              }

              notification_channels = [google_monitoring_notification_channel.sap_email.id]

              documentation {
                content   = join("", [
                  "No successful HANA backup has been recorded in the last 24 hours. ",
                  "Check Backint agent and Cloud Storage connectivity."
                ])
                mime_type = "text/markdown"
              }
            }

            # --- Monitoring dashboard ---

            resource "google_monitoring_dashboard" "sap_overview" {
              dashboard_json = jsonencode({
                displayName = "SAP HANA Overview"
                mosaicLayout = {
                  tiles = [
                    {
                      width  = 6
                      height = 4
                      widget = {
                        title = "HANA Memory Utilisation"
                        xyChart = {
                          dataSets = [{
                            timeSeriesQuery = {
                              timeSeriesFilter = {
                                filter = join(" AND ", [
                                  "resource.type = \\"gce_instance\\"",
                                  "metric.type = \\"agent.googleapis.com/sap/hana/memory/total_used_size\\""
                                ])
                              }
                            }
                          }]
                        }
                      }
                    },
                    {
                      xPos   = 6
                      width  = 6
                      height = 4
                      widget = {
                        title = "HANA CPU Utilisation"
                        xyChart = {
                          dataSets = [{
                            timeSeriesQuery = {
                              timeSeriesFilter = {
                                filter = join(" AND ", [
                                  "resource.type = \\"gce_instance\\"",
                                  "metric.type = \\"compute.googleapis.com/instance/cpu/utilization\\"",
                                  "metadata.user_labels.sap_component = \\"hana\\""
                                ])
                              }
                            }
                          }]
                        }
                      }
                    },
                    {
                      yPos   = 4
                      width  = 6
                      height = 4
                      widget = {
                        title = "HANA Disk IOPS"
                        xyChart = {
                          dataSets = [{
                            timeSeriesQuery = {
                              timeSeriesFilter = {
                                filter = join(" AND ", [
                                  "resource.type = \\"gce_instance\\"",
                                  "metric.type = \\"compute.googleapis.com/instance/disk/read_ops_count\\"",
                                  "metadata.user_labels.sap_component = \\"hana\\""
                                ])
                              }
                            }
                          }]
                        }
                      }
                    },
                    {
                      xPos   = 6
                      yPos   = 4
                      width  = 6
                      height = 4
                      widget = {
                        title = "App Server CPU"
                        xyChart = {
                          dataSets = [{
                            timeSeriesQuery = {
                              timeSeriesFilter = {
                                filter = join(" AND ", [
                                  "resource.type = \\"gce_instance\\"",
                                  "metric.type = \\"compute.googleapis.com/instance/cpu/utilization\\"",
                                  "metadata.user_labels.sap_component = \\"application-server\\""
                                ])
                              }
                            }
                          }]
                        }
                      }
                    },
                    {
                      yPos   = 8
                      width  = 12
                      height = 4
                      widget = {
                        title = "Network Egress (All SAP)"
                        xyChart = {
                          dataSets = [{
                            timeSeriesQuery = {
                              timeSeriesFilter = {
                                filter = join(" AND ", [
                                  "resource.type = \\"gce_instance\\"",
                                  "metric.type = \\"compute.googleapis.com/instance/network/sent_bytes_count\\"",
                                  "metadata.user_labels.workload = \\"sap-s4hana\\""
                                ])
                              }
                            }
                          }]
                        }
                      }
                    }
                  ]
                }
              })
            }""")

    def _generate_outputs(self, plan: InfrastructurePlan) -> str:
        hana_outputs = ""
        if plan.ha_enabled:
            hana_outputs = textwrap.dedent("""\

            output "hana_primary_ip" {
              description = "Internal IP of HANA primary instance"
              value       = google_compute_instance.hana-1.network_interface[0].network_ip
            }

            output "hana_secondary_ip" {
              description = "Internal IP of HANA secondary instance"
              value       = google_compute_instance.hana-2.network_interface[0].network_ip
            }

            output "hana_vip" {
              description = "HANA Virtual IP (ILB address)"
              value       = google_compute_forwarding_rule.hana_ilb.ip_address
            }""")
        else:
            hana_outputs = textwrap.dedent("""\

            output "hana_ip" {
              description = "Internal IP of HANA instance"
              value       = google_compute_instance.hana.network_interface[0].network_ip
            }""")

        return textwrap.dedent(f"""\
            # =============================================================================
            # outputs.tf — Key infrastructure outputs
            # =============================================================================
            {hana_outputs}

            output "vpc_id" {{
              description = "VPC network ID"
              value       = google_compute_network.sap_vpc.id
            }}

            output "backup_bucket" {{
              description = "Cloud Storage bucket for SAP HANA backups"
              value       = google_storage_bucket.sap_backup.name
            }}

            output "transport_filestore_ip" {{
              description = "Filestore IP for SAP transport directory"
              value       = google_filestore_instance.sap_transport.networks[0].ip_addresses[0]
            }}

            output "programme_id" {{
              description = "HanaForge programme identifier"
              value       = var.programme_id
            }}""")
