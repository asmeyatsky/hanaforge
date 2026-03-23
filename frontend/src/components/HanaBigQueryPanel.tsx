import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient, APIError } from '../api/client';
import type {
  DataPipelineResponse,
  PipelineRunResponse,
  ValidatePipelineResponse,
} from '../types';

const LANDSCAPE_KEY = (programmeId: string) => `hanaforge_landscape_${programmeId}`;

export default function HanaBigQueryPanel() {
  const { id: programmeId } = useParams<{ id: string }>();

  const [landscapeId, setLandscapeId] = useState<string>('');
  const [pipelines, setPipelines] = useState<DataPipelineResponse[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>('');
  const [runs, setRuns] = useState<PipelineRunResponse[]>([]);

  const [pipelineName, setPipelineName] = useState('Demo — HANA to BigQuery');
  const [sourceSchema, setSourceSchema] = useState('SYS');
  const [sourceTable, setSourceTable] = useState('TABLES');
  const [targetDataset, setTargetDataset] = useState('hana_forge_demo');
  const [targetTable, setTargetTable] = useState('sys_tables');
  const [rowLimit, setRowLimit] = useState(5);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [validateResult, setValidateResult] = useState<ValidatePipelineResponse | null>(null);
  const [lastRun, setLastRun] = useState<PipelineRunResponse | null>(null);

  const refreshPipelines = useCallback(async () => {
    if (!programmeId) return;
    const { pipelines: list } = await apiClient.listHanaBigQueryPipelines(programmeId);
    setPipelines(list);
    setSelectedPipelineId((prev) =>
      prev && list.some((x) => x.id === prev) ? prev : (list[0]?.id ?? ''),
    );
  }, [programmeId]);

  useEffect(() => {
    if (!programmeId) return;
    try {
      const stored = sessionStorage.getItem(LANDSCAPE_KEY(programmeId));
      if (stored) setLandscapeId(stored);
    } catch {
      /* ignore */
    }
  }, [programmeId]);

  useEffect(() => {
    if (!programmeId) return;
    (async () => {
      try {
        await refreshPipelines();
      } catch {
        /* empty */
      }
    })();
  }, [programmeId, refreshPipelines]);

  useEffect(() => {
    if (!programmeId || !selectedPipelineId) {
      setRuns([]);
      return;
    }
    (async () => {
      try {
        const { runs: r } = await apiClient.listHanaBigQueryRuns(programmeId, selectedPipelineId);
        setRuns(r);
      } catch {
        setRuns([]);
      }
    })();
  }, [programmeId, selectedPipelineId, lastRun]);

  const handleDiscover = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const d = await apiClient.startDiscovery(programmeId, {});
      setLandscapeId(d.landscape_id);
      sessionStorage.setItem(LANDSCAPE_KEY(programmeId), d.landscape_id);
      setInfo(`Discovery complete. landscape_id=${d.landscape_id}`);
    } catch (e) {
      setError(e instanceof APIError ? e.message : 'Discovery failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePipeline = async () => {
    if (!programmeId || !landscapeId.trim()) {
      setError('Run discovery first to obtain a landscape_id.');
      return;
    }
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const p = await apiClient.createHanaBigQueryPipeline(programmeId, {
        landscape_id: landscapeId.trim(),
        name: pipelineName.trim() || 'Untitled pipeline',
        replication_mode: 'full',
        table_mappings: [
          {
            source_schema: sourceSchema.trim(),
            source_table: sourceTable.trim(),
            target_dataset: targetDataset.trim(),
            target_table: targetTable.trim(),
          },
        ],
      });
      setSelectedPipelineId(p.id);
      setInfo(`Pipeline created: ${p.id}`);
      await refreshPipelines();
    } catch (e) {
      setError(e instanceof APIError ? e.message : 'Create pipeline failed');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!programmeId || !selectedPipelineId) return;
    setLoading(true);
    setError(null);
    try {
      const v = await apiClient.validateHanaBigQueryPipeline(programmeId, selectedPipelineId, {});
      setValidateResult(v);
    } catch (e) {
      setError(e instanceof APIError ? e.message : 'Validate failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if (!programmeId || !selectedPipelineId) return;
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const run = await apiClient.startHanaBigQueryRun(programmeId, selectedPipelineId, {
        row_limit_per_table: rowLimit,
      });
      setLastRun(run);
      setInfo(`Run ${run.id} — status ${run.status}`);
    } catch (e) {
      setError(e instanceof APIError ? e.message : 'Run failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">HANA → BigQuery</h1>
        <p className="mt-1 text-sm text-slate-500">
          Define table mappings, validate HANA connectivity, and run extract → stage → load (stub or real, per
          backend configuration).
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}
      {info && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {info}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card p-6 space-y-4">
          <h2 className="text-base font-semibold text-slate-900">1. Landscape</h2>
          <p className="text-xs text-slate-500">
            Pipelines require a landscape from discovery. Uses the real API:{' '}
            <code className="text-xs bg-slate-100 px-1 rounded">POST /api/v1/discovery/&#123;id&#125;/discover</code>
          </p>
          <div className="flex flex-wrap gap-3 items-end">
            <button type="button" className="btn-primary" disabled={loading} onClick={handleDiscover}>
              Run discovery (stub SAP)
            </button>
            <div className="flex-1 min-w-[200px]">
              <label className="label">landscape_id</label>
              <input
                className="input font-mono text-sm"
                value={landscapeId}
                onChange={(e) => setLandscapeId(e.target.value)}
                placeholder="Paste or discover…"
              />
            </div>
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h2 className="text-base font-semibold text-slate-900">2. New pipeline</h2>
          <div>
            <label className="label">Pipeline name</label>
            <input className="input" value={pipelineName} onChange={(e) => setPipelineName(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">HANA schema</label>
              <input className="input font-mono text-sm" value={sourceSchema} onChange={(e) => setSourceSchema(e.target.value)} />
            </div>
            <div>
              <label className="label">HANA table</label>
              <input className="input font-mono text-sm" value={sourceTable} onChange={(e) => setSourceTable(e.target.value)} />
            </div>
            <div>
              <label className="label">BQ dataset</label>
              <input className="input font-mono text-sm" value={targetDataset} onChange={(e) => setTargetDataset(e.target.value)} />
            </div>
            <div>
              <label className="label">BQ table</label>
              <input className="input font-mono text-sm" value={targetTable} onChange={(e) => setTargetTable(e.target.value)} />
            </div>
          </div>
          <button type="button" className="btn-primary" disabled={loading} onClick={handleCreatePipeline}>
            Create pipeline
          </button>
        </div>
      </div>

      <div className="card p-6 space-y-4">
        <h2 className="text-base font-semibold text-slate-900">3. Run</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div className="min-w-[220px] flex-1">
            <label className="label">Pipeline</label>
            <select
              className="input"
              value={selectedPipelineId}
              onChange={(e) => setSelectedPipelineId(e.target.value)}
            >
              <option value="">— select —</option>
              {pipelines.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.id.slice(0, 8)}…)
                </option>
              ))}
            </select>
          </div>
          <div className="w-28">
            <label className="label">Row limit</label>
            <input
              type="number"
              min={1}
              max={10000}
              className="input"
              value={rowLimit}
              onChange={(e) => setRowLimit(Number(e.target.value) || 5)}
            />
          </div>
          <button type="button" className="btn-secondary" disabled={loading || !selectedPipelineId} onClick={handleValidate}>
            Validate HANA
          </button>
          <button type="button" className="btn-primary" disabled={loading || !selectedPipelineId} onClick={handleRun}>
            Run pipeline
          </button>
        </div>
        {validateResult && (
          <p className="text-sm text-slate-600">
            <span className={validateResult.hana_reachable ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'}>
              {validateResult.hana_reachable ? 'Reachable' : 'Not reachable'}
            </span>
            {' — '}
            {validateResult.message}
          </p>
        )}
      </div>

      {lastRun && (
        <div className="card p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-3">Last run</h2>
          <p className="text-xs text-slate-500 mb-2 font-mono">
            {lastRun.id} · {lastRun.status}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b">
                  <th className="py-2 pr-4">Source</th>
                  <th className="py-2 pr-4">Target</th>
                  <th className="py-2 pr-4">Phase</th>
                  <th className="py-2 pr-4">Rows</th>
                  <th className="py-2 pr-4">Staging</th>
                  <th className="py-2">Job</th>
                </tr>
              </thead>
              <tbody>
                {lastRun.table_results.map((t, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="py-2 pr-4 font-mono text-xs">
                      {t.source_schema}.{t.source_table}
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs">
                      {t.target_dataset}.{t.target_table}
                    </td>
                    <td className="py-2 pr-4">{t.phase_reached}</td>
                    <td className="py-2 pr-4">
                      {t.rows_extracted}
                      {t.rows_loaded != null ? ` → ${t.rows_loaded}` : ''}
                    </td>
                    <td className="py-2 pr-4 text-xs truncate max-w-[180px]" title={t.staging_uri ?? ''}>
                      {t.staging_uri ?? '—'}
                    </td>
                    <td className="py-2 text-xs font-mono">{t.bq_job_id ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {runs.length > 0 && (
        <div className="card p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-3">Recent runs</h2>
          <ul className="text-sm space-y-2">
            {runs.slice(0, 8).map((r) => (
              <li key={r.id} className="flex justify-between gap-4 border-b border-slate-100 py-2">
                <span className="font-mono text-xs text-slate-600">{r.id}</span>
                <span className="text-slate-500">{new Date(r.started_at).toLocaleString()}</span>
                <span className="font-medium">{r.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
