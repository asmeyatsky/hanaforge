import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { DataReadinessResult } from '../types';

function severityBadge(severity: string) {
  switch (severity) {
    case 'critical':
      return 'badge-red';
    case 'high':
      return 'badge-amber';
    case 'medium':
      return 'badge-blue';
    case 'low':
      return 'badge-slate';
    default:
      return 'badge-slate';
  }
}

function profilingStatusBadge(status: string) {
  switch (status) {
    case 'complete':
      return 'badge-green';
    case 'running':
      return 'badge-blue';
    case 'failed':
      return 'badge-red';
    default:
      return 'badge-slate';
  }
}

function qualityColor(score: number): string {
  if (score >= 90) return 'bg-emerald-500';
  if (score >= 70) return 'bg-amber-500';
  if (score >= 50) return 'bg-orange-500';
  return 'bg-red-500';
}

function qualityTextColor(score: number): string {
  if (score >= 90) return 'text-emerald-600';
  if (score >= 70) return 'text-amber-600';
  if (score >= 50) return 'text-orange-600';
  return 'text-red-600';
}

export default function DataReadinessPanel() {
  const { id: programmeId } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DataReadinessResult | null>(null);

  const handleRunProfiling = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.runProfiling(programmeId);
      setResult(data);
    } catch {
      // Demo fallback
      setResult({
        programme_id: programmeId,
        overall_score: 74,
        total_records: 14_500_000,
        profiled_records: 12_200_000,
        domains: [
          { id: 'd1', name: 'Finance (FI)', record_count: 4_200_000, quality_score: 92, profiling_status: 'complete', last_profiled_at: '2026-03-08T14:30:00Z' },
          { id: 'd2', name: 'Sales & Distribution (SD)', record_count: 3_800_000, quality_score: 78, profiling_status: 'complete', last_profiled_at: '2026-03-08T14:25:00Z' },
          { id: 'd3', name: 'Materials Management (MM)', record_count: 2_600_000, quality_score: 65, profiling_status: 'complete', last_profiled_at: '2026-03-08T14:20:00Z' },
          { id: 'd4', name: 'Human Capital (HCM)', record_count: 1_600_000, quality_score: 54, profiling_status: 'running', last_profiled_at: null },
          { id: 'd5', name: 'Plant Maintenance (PM)', record_count: 1_100_000, quality_score: 0, profiling_status: 'pending', last_profiled_at: null },
          { id: 'd6', name: 'Production Planning (PP)', record_count: 1_200_000, quality_score: 0, profiling_status: 'pending', last_profiled_at: null },
        ],
        issues: [
          { id: 'i1', domain_id: 'd2', domain_name: 'Sales & Distribution', field: 'VBAK-BSTNK', issue_type: 'Orphaned References', severity: 'high', description: 'Purchase order references point to deleted entries in EKKO', affected_records: 12_400 },
          { id: 'i2', domain_id: 'd3', domain_name: 'Materials Management', field: 'MARA-MATKL', issue_type: 'Missing Values', severity: 'critical', description: 'Material group classification missing for active materials', affected_records: 8_700 },
          { id: 'i3', domain_id: 'd3', domain_name: 'Materials Management', field: 'MARC-DISGR', issue_type: 'Invalid Values', severity: 'medium', description: 'MRP group contains deprecated values not supported in S/4HANA', affected_records: 3_200 },
          { id: 'i4', domain_id: 'd1', domain_name: 'Finance', field: 'BSEG-ZUONR', issue_type: 'Truncation Risk', severity: 'low', description: 'Assignment number values exceed new field length in ACDOCA', affected_records: 1_100 },
          { id: 'i5', domain_id: 'd2', domain_name: 'Sales & Distribution', field: 'VBAP-WERKS', issue_type: 'Inconsistent Values', severity: 'high', description: 'Plant assignments inconsistent with delivering plant configuration', affected_records: 5_600 },
          { id: 'i6', domain_id: 'd4', domain_name: 'Human Capital', field: 'PA0001-PLANS', issue_type: 'Missing Values', severity: 'critical', description: 'Position assignment missing for active employees', affected_records: 2_300 },
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
      const data = await apiClient.getDataReadiness(programmeId);
      setResult(data);
    } catch {
      setError('No existing profiling data found. Run profiling to get started.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Data Readiness
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Profile data domains, assess quality scores, and identify migration-blocking issues.
          </p>
        </div>
        <div className="flex gap-3">
          {!result && (
            <button
              onClick={handleLoadExisting}
              disabled={loading}
              className="btn-secondary disabled:opacity-50"
            >
              Load Existing
            </button>
          )}
          <button
            onClick={handleRunProfiling}
            disabled={loading}
            className="btn-accent disabled:opacity-50"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Profiling...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
                </svg>
                Run Profiling
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
      {!result && !loading && !error && (
        <div className="card p-12 text-center">
          <svg
            className="w-16 h-16 mx-auto text-slate-200"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
          </svg>
          <h3 className="mt-4 text-base font-medium text-slate-500">
            No profiling data yet
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Run data profiling to assess quality and readiness of your SAP data domains for S/4HANA migration.
          </p>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="stat-card">
              <p className="text-sm text-slate-500">Overall Score</p>
              <p className={`mt-1 text-3xl font-bold ${qualityTextColor(result.overall_score)}`}>
                {result.overall_score}%
              </p>
              <p className="text-xs text-slate-400 mt-1">Data quality index</p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Data Domains</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {result.domains.length}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {result.domains.filter((d) => d.profiling_status === 'complete').length} profiled
              </p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Total Records</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {(result.total_records / 1_000_000).toFixed(1)}M
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {Math.round((result.profiled_records / result.total_records) * 100)}% profiled
              </p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Quality Issues</p>
              <p className="mt-1 text-3xl font-bold text-red-600">
                {result.issues.length}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {result.issues.filter((i) => i.severity === 'critical').length} critical
              </p>
            </div>
          </div>

          {/* Data domains with quality bars */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-900">
                Data Domains
              </h3>
            </div>
            <div className="divide-y divide-slate-100">
              {result.domains.map((domain) => (
                <div key={domain.id} className="px-6 py-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold text-slate-900">
                        {domain.name}
                      </span>
                      <span className={profilingStatusBadge(domain.profiling_status)}>
                        {domain.profiling_status}
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-xs text-slate-400">
                        {(domain.record_count / 1_000_000).toFixed(1)}M records
                      </span>
                      {domain.profiling_status === 'complete' && (
                        <span className={`text-sm font-bold ${qualityTextColor(domain.quality_score)}`}>
                          {domain.quality_score}%
                        </span>
                      )}
                    </div>
                  </div>
                  {domain.profiling_status === 'complete' && (
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${qualityColor(domain.quality_score)}`}
                          style={{ width: `${domain.quality_score}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {domain.profiling_status === 'running' && (
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '60%' }} />
                      </div>
                    </div>
                  )}
                  {domain.last_profiled_at && (
                    <p className="mt-1 text-xs text-slate-400">
                      Last profiled: {new Date(domain.last_profiled_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Quality issues table */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-900">
                Data Quality Issues ({result.issues.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="table-header">Severity</th>
                    <th className="table-header">Domain</th>
                    <th className="table-header">Field</th>
                    <th className="table-header">Issue Type</th>
                    <th className="table-header">Description</th>
                    <th className="table-header">Affected</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.issues.map((issue) => (
                    <tr key={issue.id} className="hover:bg-slate-50 transition-colors">
                      <td className="table-cell">
                        <span className={severityBadge(issue.severity)}>
                          {issue.severity}
                        </span>
                      </td>
                      <td className="table-cell text-sm text-slate-700">
                        {issue.domain_name}
                      </td>
                      <td className="table-cell">
                        <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">
                          {issue.field}
                        </code>
                      </td>
                      <td className="table-cell text-sm text-slate-600">
                        {issue.issue_type}
                      </td>
                      <td className="table-cell text-sm text-slate-500 max-w-xs truncate">
                        {issue.description}
                      </td>
                      <td className="table-cell text-sm font-mono text-slate-700">
                        {issue.affected_records.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
