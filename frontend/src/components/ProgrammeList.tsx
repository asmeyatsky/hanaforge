import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Programme, CreateProgrammeRequest } from '../types';

// --------------------------------------------------------------------------
// Create Programme Form (modal)
// --------------------------------------------------------------------------

function CreateProgrammeForm({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<CreateProgrammeRequest>({
    name: '',
    customer_id: '',
    sap_source_version: 'ECC 6.0',
    target_version: 'S/4HANA 2023',
    go_live_date: null,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiClient.createProgramme(form);
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create programme');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <h2 className="text-lg font-semibold text-slate-900">
            Create New Programme
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-danger-50 border border-danger-200 rounded-lg text-sm text-danger-700">
              {error}
            </div>
          )}

          <div>
            <label className="label">Programme Name</label>
            <input
              className="input"
              placeholder="e.g. Acme Corp S/4HANA Migration"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="label">Customer ID</label>
            <input
              className="input"
              placeholder="e.g. ACME-001"
              value={form.customer_id}
              onChange={(e) =>
                setForm({ ...form, customer_id: e.target.value })
              }
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Source SAP Version</label>
              <select
                className="input"
                value={form.sap_source_version}
                onChange={(e) =>
                  setForm({ ...form, sap_source_version: e.target.value })
                }
              >
                <option value="ECC 6.0">ECC 6.0</option>
                <option value="ECC 5.0">ECC 5.0</option>
                <option value="R/3 4.7">R/3 4.7</option>
                <option value="S/4HANA 1909">S/4HANA 1909</option>
                <option value="S/4HANA 2020">S/4HANA 2020</option>
              </select>
            </div>
            <div>
              <label className="label">Target Version</label>
              <select
                className="input"
                value={form.target_version}
                onChange={(e) =>
                  setForm({ ...form, target_version: e.target.value })
                }
              >
                <option value="S/4HANA 2023">S/4HANA 2023</option>
                <option value="S/4HANA 2024">S/4HANA 2024</option>
                <option value="S/4HANA Cloud">S/4HANA Cloud</option>
              </select>
            </div>
          </div>

          <div>
            <label className="label">Target Go-Live Date (optional)</label>
            <input
              type="date"
              className="input"
              value={form.go_live_date ?? ''}
              onChange={(e) =>
                setForm({
                  ...form,
                  go_live_date: e.target.value || null,
                })
              }
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !form.name || !form.customer_id}
              className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creating...
                </>
              ) : (
                'Create Programme'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// Status badge helper
// --------------------------------------------------------------------------

function statusBadge(status: string) {
  const s = status.toLowerCase();
  if (s.includes('complete') || s === 'completed') return 'badge-green';
  if (s.includes('progress')) return 'badge-blue';
  if (s === 'created') return 'badge-slate';
  if (s.includes('ready') || s.includes('cutover') || s.includes('hypercare'))
    return 'badge-amber';
  return 'badge-slate';
}

// --------------------------------------------------------------------------
// Main component
// --------------------------------------------------------------------------

export default function ProgrammeList() {
  const navigate = useNavigate();
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const loadProgrammes = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiClient.listProgrammes();
      setProgrammes(result.programmes);
    } catch {
      // In demo mode, use placeholder data when API is unreachable
      setProgrammes([
        {
          id: 'demo-1',
          name: 'Acme Corp ECC Migration',
          customer_id: 'ACME-001',
          sap_source_version: 'ECC 6.0',
          target_version: 'S/4HANA 2023',
          status: 'DISCOVERY_COMPLETE',
          complexity_score: { score: 67, risk_level: 'HIGH', benchmark_percentile: 72 },
          created_at: '2026-01-15T10:30:00Z',
        },
        {
          id: 'demo-2',
          name: 'Global Industries S/4 Upgrade',
          customer_id: 'GLOB-042',
          sap_source_version: 'S/4HANA 1909',
          target_version: 'S/4HANA 2024',
          status: 'ANALYSIS_IN_PROGRESS',
          complexity_score: { score: 34, risk_level: 'MEDIUM', benchmark_percentile: 45 },
          created_at: '2026-02-20T14:00:00Z',
        },
        {
          id: 'demo-3',
          name: 'TechCo Migration 2026',
          customer_id: 'TECH-007',
          sap_source_version: 'ECC 6.0',
          target_version: 'S/4HANA Cloud',
          status: 'CREATED',
          complexity_score: null,
          created_at: '2026-03-05T09:15:00Z',
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProgrammes();
  }, [loadProgrammes]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Programmes</h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage SAP S/4HANA migration programmes
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Programme
        </button>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <svg className="animate-spin w-8 h-8 text-primary-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        ) : programmes.length === 0 ? (
          <div className="text-center py-20">
            <svg className="w-12 h-12 mx-auto text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
            </svg>
            <h3 className="mt-4 text-sm font-medium text-slate-900">
              No programmes yet
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Create your first migration programme to get started.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="btn-primary mt-4"
            >
              Create Programme
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="table-header">Programme Name</th>
                  <th className="table-header">Customer</th>
                  <th className="table-header">SAP Version</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Complexity</th>
                  <th className="table-header">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {programmes.map((prog) => (
                  <tr
                    key={prog.id}
                    onClick={() => navigate(`/programmes/${prog.id}`)}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <td className="table-cell font-semibold text-slate-900">
                      {prog.name}
                    </td>
                    <td className="table-cell">
                      <span className="font-mono text-xs bg-slate-100 px-2 py-1 rounded">
                        {prog.customer_id}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className="text-slate-500">
                        {prog.sap_source_version}
                      </span>
                      <svg className="inline w-4 h-4 mx-1 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                      </svg>
                      <span className="text-slate-700 font-medium">
                        {prog.target_version}
                      </span>
                    </td>
                    <td className="table-cell">
                      <span className={statusBadge(prog.status)}>
                        {prog.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="table-cell">
                      {prog.complexity_score ? (
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-lg font-bold ${
                              prog.complexity_score.score <= 25
                                ? 'text-emerald-600'
                                : prog.complexity_score.score <= 50
                                  ? 'text-amber-600'
                                  : prog.complexity_score.score <= 75
                                    ? 'text-orange-600'
                                    : 'text-red-600'
                            }`}
                          >
                            {prog.complexity_score.score}
                          </span>
                          <span className="text-[10px] text-slate-400 uppercase font-semibold">
                            {prog.complexity_score.risk_level}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">--</span>
                      )}
                    </td>
                    <td className="table-cell text-slate-500">
                      {new Date(prog.created_at).toLocaleDateString('en-GB', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create modal */}
      {showCreate && (
        <CreateProgrammeForm
          onClose={() => setShowCreate(false)}
          onCreated={loadProgrammes}
        />
      )}
    </div>
  );
}
