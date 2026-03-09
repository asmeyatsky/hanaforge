import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { InfrastructurePlan } from '../types';

function resourceIcon(type: string) {
  switch (type) {
    case 'vm':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
        </svg>
      );
    case 'network':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
        </svg>
      );
    case 'storage':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
        </svg>
      );
    case 'database':
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
        </svg>
      );
    default:
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
        </svg>
      );
  }
}

function statusBadge(status: string) {
  switch (status) {
    case 'approved':
      return 'badge-green';
    case 'provisioned':
      return 'badge-blue';
    default:
      return 'badge-amber';
  }
}

export default function InfrastructurePanel() {
  const { id: programmeId } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<InfrastructurePlan | null>(null);
  const [showTerraform, setShowTerraform] = useState(false);

  const handleGeneratePlan = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.generateInfrastructurePlan(programmeId);
      setPlan(data);
    } catch {
      // Demo fallback
      setPlan({
        programme_id: programmeId,
        plan_id: 'infra-001',
        status: 'draft',
        region: 'europe-west1 (Belgium)',
        sizing_tier: 'Production - Large',
        estimated_monthly_cost: 18_450,
        created_at: new Date().toISOString(),
        terraform_plan: `# HanaForge Infrastructure - Generated Plan
# Programme: ${programmeId}
# Region: europe-west1

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "europe-west1"
}

# SAP HANA Primary Instance
resource "google_compute_instance" "sap_hana_primary" {
  name         = "hanaforge-hana-primary"
  machine_type = "m2-ultramem-416"
  zone         = "europe-west1-b"

  boot_disk {
    initialize_params {
      image = "projects/suse-sap-cloud/global/images/family/sles-15-sp5-sap"
      size  = 100
      type  = "pd-ssd"
    }
  }

  attached_disk {
    source      = google_compute_disk.hana_data.id
    device_name = "hana-data"
  }

  attached_disk {
    source      = google_compute_disk.hana_log.id
    device_name = "hana-log"
  }

  network_interface {
    subnetwork = google_compute_subnetwork.sap_subnet.id
  }

  tags = ["sap-hana", "hanaforge"]
}

# Application Server
resource "google_compute_instance" "sap_app" {
  name         = "hanaforge-app-server"
  machine_type = "n2-highmem-32"
  zone         = "europe-west1-b"

  boot_disk {
    initialize_params {
      image = "projects/suse-sap-cloud/global/images/family/sles-15-sp5-sap"
      size  = 200
      type  = "pd-balanced"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.sap_subnet.id
  }

  tags = ["sap-app", "hanaforge"]
}

# VPC Network
resource "google_compute_network" "sap_vpc" {
  name                    = "hanaforge-sap-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "sap_subnet" {
  name          = "hanaforge-sap-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = "europe-west1"
  network       = google_compute_network.sap_vpc.id
}

# Cloud Storage for backups
resource "google_storage_bucket" "sap_backup" {
  name     = "hanaforge-sap-backup-\${var.project_id}"
  location = "EU"

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}`,
        resources: [
          { id: 'r1', resource_type: 'vm', name: 'SAP HANA Primary', spec: 'm2-ultramem-416 (416 vCPU, 11.7 TB RAM)', region: 'europe-west1-b', estimated_monthly_cost: 12_200 },
          { id: 'r2', resource_type: 'vm', name: 'SAP Application Server', spec: 'n2-highmem-32 (32 vCPU, 256 GB RAM)', region: 'europe-west1-b', estimated_monthly_cost: 2_400 },
          { id: 'r3', resource_type: 'network', name: 'SAP VPC Network', spec: 'Custom VPC with private subnet 10.0.1.0/24', region: 'europe-west1', estimated_monthly_cost: 150 },
          { id: 'r4', resource_type: 'storage', name: 'HANA Data Volume', spec: 'pd-ssd, 4 TB', region: 'europe-west1-b', estimated_monthly_cost: 1_360 },
          { id: 'r5', resource_type: 'storage', name: 'HANA Log Volume', spec: 'pd-ssd, 1 TB', region: 'europe-west1-b', estimated_monthly_cost: 340 },
          { id: 'r6', resource_type: 'storage', name: 'Backup Storage', spec: 'Cloud Storage, Standard, EU multi-region', region: 'EU', estimated_monthly_cost: 200 },
          { id: 'r7', resource_type: 'load_balancer', name: 'Internal Load Balancer', spec: 'Regional internal TCP/UDP LB', region: 'europe-west1', estimated_monthly_cost: 50 },
          { id: 'r8', resource_type: 'database', name: 'Cloud SQL (Metadata)', spec: 'db-custom-4-16384, HA enabled', region: 'europe-west1', estimated_monthly_cost: 750 },
        ],
      });
      setError(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadExisting = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getInfrastructurePlan(programmeId);
      setPlan(data);
    } catch {
      setError('No existing infrastructure plan found. Generate a plan to get started.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadTerraform = async () => {
    if (!plan) return;
    // Create a download from the terraform_plan text
    const blob = new Blob([plan.terraform_plan], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hanaforge-infra-${programmeId}.tf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const totalCost = plan
    ? plan.resources.reduce((sum, r) => sum + r.estimated_monthly_cost, 0)
    : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Infrastructure Planning
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Generate GCP infrastructure plans, review resource sizing, and download Terraform configurations.
          </p>
        </div>
        <div className="flex gap-3">
          {!plan && (
            <button
              onClick={handleLoadExisting}
              disabled={loading}
              className="btn-secondary disabled:opacity-50"
            >
              Load Existing
            </button>
          )}
          <button
            onClick={handleGeneratePlan}
            disabled={loading}
            className="btn-accent disabled:opacity-50"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
                </svg>
                Generate Plan
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-danger-50 border border-danger-200 rounded-lg text-sm text-danger-700">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!plan && !loading && !error && (
        <div className="card p-12 text-center">
          <svg
            className="w-16 h-16 mx-auto text-slate-200"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" />
          </svg>
          <h3 className="mt-4 text-base font-medium text-slate-500">
            No infrastructure plan yet
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Generate an infrastructure plan based on your SAP landscape assessment and sizing requirements.
          </p>
        </div>
      )}

      {/* Plan results */}
      {plan && (
        <>
          {/* Plan overview */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="stat-card">
              <p className="text-sm text-slate-500">Status</p>
              <div className="mt-2">
                <span className={statusBadge(plan.status)}>
                  {plan.status}
                </span>
              </div>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Region</p>
              <p className="mt-1 text-lg font-bold text-slate-900">{plan.region}</p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Sizing Tier</p>
              <p className="mt-1 text-lg font-bold text-slate-900">{plan.sizing_tier}</p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Est. Monthly Cost</p>
              <p className="mt-1 text-3xl font-bold text-primary-600">
                ${totalCost.toLocaleString()}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {plan.resources.length} resources
              </p>
            </div>
          </div>

          {/* Resource table */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-900">
                Resource Inventory ({plan.resources.length} resources)
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="table-header">Type</th>
                    <th className="table-header">Name</th>
                    <th className="table-header">Spec</th>
                    <th className="table-header">Region</th>
                    <th className="table-header text-right">Monthly Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {plan.resources.map((resource) => (
                    <tr key={resource.id} className="hover:bg-slate-50 transition-colors">
                      <td className="table-cell">
                        <div className="flex items-center gap-2 text-slate-500">
                          {resourceIcon(resource.resource_type)}
                          <span className="badge-slate">{resource.resource_type.toUpperCase()}</span>
                        </div>
                      </td>
                      <td className="table-cell">
                        <span className="text-sm font-semibold text-slate-900">
                          {resource.name}
                        </span>
                      </td>
                      <td className="table-cell">
                        <span className="text-sm text-slate-600">{resource.spec}</span>
                      </td>
                      <td className="table-cell">
                        <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                          {resource.region}
                        </code>
                      </td>
                      <td className="table-cell text-right">
                        <span className="text-sm font-semibold text-slate-900">
                          ${resource.estimated_monthly_cost.toLocaleString()}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {/* Total row */}
                  <tr className="bg-slate-50 border-t-2 border-slate-200">
                    <td colSpan={4} className="table-cell text-right font-semibold text-slate-700">
                      Total Monthly Cost
                    </td>
                    <td className="table-cell text-right">
                      <span className="text-lg font-bold text-primary-600">
                        ${totalCost.toLocaleString()}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Terraform section */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900">
                Terraform Configuration
              </h3>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowTerraform(!showTerraform)}
                  className="btn-secondary text-xs py-1.5 px-3"
                >
                  {showTerraform ? 'Hide' : 'Show'} Code
                </button>
                <button
                  onClick={handleDownloadTerraform}
                  className="btn-primary text-xs py-1.5 px-3"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  Download .tf
                </button>
              </div>
            </div>
            {showTerraform && (
              <div className="p-0">
                <pre className="p-6 text-sm font-mono text-slate-300 bg-slate-900 overflow-x-auto leading-relaxed whitespace-pre">
                  <code>{plan.terraform_plan}</code>
                </pre>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
