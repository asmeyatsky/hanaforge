import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient, APIError } from '../api/client';
import type {
  DataPipelineResponse,
  HanaBqTableMappingRequest,
  PipelineRunResponse,
  TableRunRecordResponse,
  ValidatePipelineResponse,
} from '../types';

// ---------------------------------------------------------------------------
// Synthetic catalog data (client-side only — drives dropdowns & schema preview)
// ---------------------------------------------------------------------------

const LANDSCAPE_KEY = (pid: string) => `hanaforge_landscape_${pid}`;

const HANA_CATALOG: Record<string, string[]> = {
  SYS: ['TABLES', 'COLUMNS', 'VIEWS', 'SCHEMAS', 'INDEXES', 'USERS', 'PROCEDURES'],
  SAPSR3: ['MARA', 'MARC', 'MARD', 'BKPF', 'BSEG', 'VBAK', 'VBAP', 'EKKO', 'EKPO', 'KNA1', 'LFA1', 'DD02L', 'DD03L', 'TSTC'],
  SAPHANADB: ['M_TABLES', 'M_COLUMNS', 'M_CONNECTIONS', 'M_SQL_PLAN_CACHE', 'M_SERVICE_MEMORY', 'M_HEAP_MEMORY', 'M_HOST_RESOURCE_UTILIZATION'],
  _SCHEMA_INFO: ['SCHEMAS', 'TABLES', 'COLUMNS', 'TABLE_COLUMNS'],
};
const SCHEMAS = Object.keys(HANA_CATALOG);

/** Synthetic column metadata for schema preview. */
const TABLE_COLUMNS: Record<string, { name: string; type: string; key: boolean }[]> = {
  MARA: [{ name: 'MANDT', type: 'NVARCHAR(3)', key: true }, { name: 'MATNR', type: 'NVARCHAR(18)', key: true }, { name: 'MTART', type: 'NVARCHAR(4)', key: false }, { name: 'MBRSH', type: 'NVARCHAR(1)', key: false }, { name: 'MATKL', type: 'NVARCHAR(9)', key: false }, { name: 'MEINS', type: 'NVARCHAR(3)', key: false }, { name: 'BRGEW', type: 'DECIMAL(13,3)', key: false }, { name: 'NTGEW', type: 'DECIMAL(13,3)', key: false }],
  BKPF: [{ name: 'MANDT', type: 'NVARCHAR(3)', key: true }, { name: 'BUKRS', type: 'NVARCHAR(4)', key: true }, { name: 'BELNR', type: 'NVARCHAR(10)', key: true }, { name: 'GJAHR', type: 'NVARCHAR(4)', key: true }, { name: 'BLART', type: 'NVARCHAR(2)', key: false }, { name: 'BUDAT', type: 'DATE', key: false }, { name: 'MONAT', type: 'NVARCHAR(2)', key: false }, { name: 'WAERS', type: 'NVARCHAR(5)', key: false }],
  VBAK: [{ name: 'MANDT', type: 'NVARCHAR(3)', key: true }, { name: 'VBELN', type: 'NVARCHAR(10)', key: true }, { name: 'ERDAT', type: 'DATE', key: false }, { name: 'ERZET', type: 'TIME', key: false }, { name: 'ERNAM', type: 'NVARCHAR(12)', key: false }, { name: 'AUART', type: 'NVARCHAR(4)', key: false }, { name: 'NETWR', type: 'DECIMAL(15,2)', key: false }, { name: 'WAERK', type: 'NVARCHAR(5)', key: false }],
  EKKO: [{ name: 'MANDT', type: 'NVARCHAR(3)', key: true }, { name: 'EBELN', type: 'NVARCHAR(10)', key: true }, { name: 'BUKRS', type: 'NVARCHAR(4)', key: false }, { name: 'BSTYP', type: 'NVARCHAR(1)', key: false }, { name: 'BSART', type: 'NVARCHAR(4)', key: false }, { name: 'LIFNR', type: 'NVARCHAR(10)', key: false }, { name: 'EKORG', type: 'NVARCHAR(4)', key: false }, { name: 'AEDAT', type: 'DATE', key: false }],
  TABLES: [{ name: 'SCHEMA_NAME', type: 'NVARCHAR(256)', key: true }, { name: 'TABLE_NAME', type: 'NVARCHAR(256)', key: true }, { name: 'TABLE_TYPE', type: 'NVARCHAR(16)', key: false }, { name: 'RECORD_COUNT', type: 'BIGINT', key: false }, { name: 'TABLE_SIZE', type: 'BIGINT', key: false }, { name: 'CREATE_TIME', type: 'TIMESTAMP', key: false }],
  KNA1: [{ name: 'MANDT', type: 'NVARCHAR(3)', key: true }, { name: 'KUNNR', type: 'NVARCHAR(10)', key: true }, { name: 'LAND1', type: 'NVARCHAR(3)', key: false }, { name: 'NAME1', type: 'NVARCHAR(35)', key: false }, { name: 'ORT01', type: 'NVARCHAR(35)', key: false }, { name: 'PSTLZ', type: 'NVARCHAR(10)', key: false }, { name: 'STRAS', type: 'NVARCHAR(35)', key: false }],
};

const BQ_DATASETS = ['hana_forge_demo', 'sap_raw', 'sap_staging', 'sap_curated', 'landing_zone'];

function suggestBqTable(schema: string, table: string): string {
  return `${schema.toLowerCase()}_${table.toLowerCase()}`;
}
function bqTableOptions(schema: string, table: string): string[] {
  const auto = suggestBqTable(schema, table);
  const lower = table.toLowerCase();
  const opts = [auto];
  if (lower !== auto) opts.push(lower);
  opts.push(`raw_${lower}`, `stg_${lower}`);
  return [...new Set(opts)];
}

/** Estimate CSV bytes for display (matches stub adapter: 4 cols ~45 bytes/row). */
function estimateBytes(rows: number): string {
  const b = rows * 45 + 40; // header
  if (b < 1024) return `${b} B`;
  return `${(b / 1024).toFixed(1)} KB`;
}

function phaseBadge(phase: string) {
  switch (phase) {
    case 'completed': return 'badge-green';
    case 'failed': return 'badge-red';
    case 'extract': case 'stage': case 'load': return 'badge-blue';
    default: return 'badge-slate';
  }
}

function runStatusBadge(status: string) {
  if (status === 'completed') return 'badge-green';
  if (status === 'failed') return 'badge-red';
  return 'badge-blue';
}

// ---------------------------------------------------------------------------
// Pipeline flow diagram
// ---------------------------------------------------------------------------

const FLOW_PHASES = ['extract', 'stage', 'load', 'completed'] as const;
const FLOW_LABELS: Record<string, string> = { extract: 'Extract', stage: 'Stage to GCS', load: 'Load to BQ', completed: 'Complete' };
const FLOW_ICONS: Record<string, string> = { extract: 'M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375', stage: 'M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.338-2.32 3.75 3.75 0 013.554 5.593A4.502 4.502 0 0118 19.5H6.75z', load: 'M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5', completed: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z' };

function phaseIndex(phase: string): number {
  const i = FLOW_PHASES.indexOf(phase as typeof FLOW_PHASES[number]);
  return i >= 0 ? i : -1;
}

function PipelineFlowDiagram({ activePhase, animating }: { activePhase: string | null; animating: boolean }) {
  const reached = activePhase ? phaseIndex(activePhase) : -1;
  return (
    <div className="flex items-center gap-1 overflow-x-auto py-2">
      {FLOW_PHASES.map((phase, idx) => {
        const done = idx < reached || (idx === reached && phase === 'completed');
        const active = idx === reached && phase !== 'completed';
        const pending = idx > reached;
        const isAnimTarget = animating && idx <= reached;
        return (
          <div key={phase} className="flex items-center gap-1">
            <div className={`flex items-center gap-2.5 rounded-lg border-2 px-4 py-3 min-w-[140px] transition-all duration-500 ${
              done ? 'border-emerald-300 bg-emerald-50' : active ? 'border-blue-400 bg-blue-50 ring-2 ring-blue-100' : 'border-slate-200 bg-white'
            }`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                done ? 'bg-emerald-500' : active ? 'bg-blue-500 animate-pulse' : 'bg-slate-200'
              }`}>
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={FLOW_ICONS[phase]} />
                </svg>
              </div>
              <div>
                <div className={`text-xs font-semibold ${done ? 'text-emerald-700' : active ? 'text-blue-700' : 'text-slate-400'}`}>
                  {FLOW_LABELS[phase]}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {done ? 'Done' : active ? (isAnimTarget ? 'Processing...' : 'Active') : pending ? 'Pending' : ''}
                </div>
              </div>
            </div>
            {idx < FLOW_PHASES.length - 1 && (
              <svg width="28" height="24" viewBox="0 0 28 24" fill="none" className="flex-shrink-0">
                <path d="M0 12h20" stroke={idx < reached ? '#10b981' : '#cbd5e1'} strokeWidth="2" />
                <path d="M16 6l6 6-6 6" stroke={idx < reached ? '#10b981' : '#cbd5e1'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Table result card
// ---------------------------------------------------------------------------

function TableResultCard({ t, durationMs }: { t: TableRunRecordResponse; durationMs: number }) {
  return (
    <div className={`rounded-lg border-2 p-4 ${
      t.phase_reached === 'completed' ? 'border-emerald-200 bg-emerald-50/30' : t.phase_reached === 'failed' ? 'border-red-200 bg-red-50/30' : 'border-slate-200'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${t.phase_reached === 'completed' ? 'bg-emerald-500' : t.phase_reached === 'failed' ? 'bg-red-500' : 'bg-blue-500 animate-pulse'}`} />
          <span className="text-sm font-semibold text-slate-800">
            {t.source_schema}.{t.source_table}
          </span>
          <svg className="w-4 h-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" /></svg>
          <span className="text-sm font-semibold text-slate-800">
            {t.target_dataset}.{t.target_table}
          </span>
        </div>
        <span className={phaseBadge(t.phase_reached)}>{t.phase_reached}</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div>
          <span className="text-slate-400 block">Rows</span>
          <span className="font-mono font-semibold text-slate-700">{t.rows_extracted} extracted{t.rows_loaded != null ? `, ${t.rows_loaded} loaded` : ''}</span>
        </div>
        <div>
          <span className="text-slate-400 block">Est. Size</span>
          <span className="font-mono font-semibold text-slate-700">{estimateBytes(t.rows_extracted)}</span>
        </div>
        <div>
          <span className="text-slate-400 block">Staging URI</span>
          <span className="font-mono text-slate-500 truncate block max-w-[200px]" title={t.staging_uri ?? ''}>{t.staging_uri ? t.staging_uri.replace(/^hanaforge-local:\/\//, '').split('/').pop() : '—'}</span>
        </div>
        <div>
          <span className="text-slate-400 block">BQ Job / Time</span>
          <span className="font-mono text-slate-500">{t.bq_job_id?.slice(0, 20) ?? '—'} &middot; {(durationMs / 1000).toFixed(1)}s</span>
        </div>
      </div>
      {t.error_message && (
        <div className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{t.error_message}</div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Schema preview
// ---------------------------------------------------------------------------

function SchemaPreview({ table }: { table: string }) {
  const cols = TABLE_COLUMNS[table];
  if (!cols) return <p className="text-xs text-slate-400 italic mt-2">No column preview for this table</p>;
  return (
    <div className="mt-3 max-h-40 overflow-y-auto rounded border border-slate-200">
      <table className="w-full text-[11px] font-mono">
        <thead className="bg-slate-50 sticky top-0">
          <tr><th className="text-left px-2 py-1 text-slate-500">Column</th><th className="text-left px-2 py-1 text-slate-500">Type</th><th className="px-2 py-1 text-slate-500">Key</th></tr>
        </thead>
        <tbody>
          {cols.map((c) => (
            <tr key={c.name} className="border-t border-slate-100"><td className="px-2 py-0.5 text-slate-700">{c.name}</td><td className="px-2 py-0.5 text-slate-500">{c.type}</td><td className="px-2 py-0.5 text-center">{c.key ? <span className="text-amber-500">PK</span> : ''}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Multi-table mapping builder
// ---------------------------------------------------------------------------

type MappingRow = { sourceSchema: string; sourceTable: string; targetDataset: string; targetTable: string };

function emptyMapping(): MappingRow {
  return { sourceSchema: 'SAPSR3', sourceTable: 'MARA', targetDataset: 'hana_forge_demo', targetTable: 'sapsr3_mara' };
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function HanaBigQueryPanel() {
  const { id: programmeId } = useParams<{ id: string }>();

  const [landscapeId, setLandscapeId] = useState('');
  const [pipelines, setPipelines] = useState<DataPipelineResponse[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState('');
  const [runs, setRuns] = useState<PipelineRunResponse[]>([]);

  const [pipelineName, setPipelineName] = useState('Demo — HANA to BigQuery');
  const [mappings, setMappings] = useState<MappingRow[]>([
    { sourceSchema: 'SAPSR3', sourceTable: 'MARA', targetDataset: 'hana_forge_demo', targetTable: 'sapsr3_mara' },
    { sourceSchema: 'SAPSR3', sourceTable: 'BKPF', targetDataset: 'hana_forge_demo', targetTable: 'sapsr3_bkpf' },
    { sourceSchema: 'SAPSR3', sourceTable: 'VBAK', targetDataset: 'hana_forge_demo', targetTable: 'sapsr3_vbak' },
  ]);
  const [rowLimit, setRowLimit] = useState(10);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [validateResult, setValidateResult] = useState<ValidatePipelineResponse | null>(null);
  const [lastRun, setLastRun] = useState<PipelineRunResponse | null>(null);

  // Animated pipeline phase during run
  const [animPhase, setAnimPhase] = useState<string | null>(null);
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshPipelines = useCallback(async () => {
    if (!programmeId) return;
    const { pipelines: list } = await apiClient.listHanaBigQueryPipelines(programmeId);
    setPipelines(list);
    setSelectedPipelineId((prev) => prev && list.some((x) => x.id === prev) ? prev : (list[0]?.id ?? ''));
  }, [programmeId]);

  useEffect(() => {
    if (!programmeId) return;
    try { const s = sessionStorage.getItem(LANDSCAPE_KEY(programmeId)); if (s) setLandscapeId(s); } catch { /* */ }
  }, [programmeId]);

  useEffect(() => {
    if (!programmeId) return;
    (async () => { try { await refreshPipelines(); } catch { /* */ } })();
  }, [programmeId, refreshPipelines]);

  useEffect(() => {
    if (!programmeId || !selectedPipelineId) { setRuns([]); return; }
    (async () => { try { const { runs: r } = await apiClient.listHanaBigQueryRuns(programmeId, selectedPipelineId); setRuns(r); } catch { setRuns([]); } })();
  }, [programmeId, selectedPipelineId, lastRun]);

  // Cleanup animation on unmount
  useEffect(() => () => { if (animRef.current) clearInterval(animRef.current); }, []);

  // --- Handlers ---

  const handleDiscover = async () => {
    if (!programmeId) return;
    setLoading(true); setError(null); setInfo(null);
    try {
      const d = await apiClient.startDiscovery(programmeId, {});
      setLandscapeId(d.landscape_id);
      sessionStorage.setItem(LANDSCAPE_KEY(programmeId), d.landscape_id);
      setInfo(`Discovery complete — landscape ${d.landscape_id.slice(0, 8)}…`);
    } catch (e) { setError(e instanceof APIError ? e.message : 'Discovery failed'); }
    finally { setLoading(false); }
  };

  const handleCreatePipeline = async () => {
    if (!programmeId || !landscapeId.trim()) { setError('Run discovery first.'); return; }
    if (mappings.length === 0) { setError('Add at least one table mapping.'); return; }
    setLoading(true); setError(null); setInfo(null);
    try {
      const tm: HanaBqTableMappingRequest[] = mappings.map((m) => ({ source_schema: m.sourceSchema, source_table: m.sourceTable, target_dataset: m.targetDataset, target_table: m.targetTable }));
      const p = await apiClient.createHanaBigQueryPipeline(programmeId, { landscape_id: landscapeId.trim(), name: pipelineName.trim() || 'Untitled', replication_mode: 'full', table_mappings: tm });
      setSelectedPipelineId(p.id);
      setInfo(`Pipeline created — ${tm.length} table(s) mapped`);
      await refreshPipelines();
    } catch (e) { setError(e instanceof APIError ? e.message : 'Create failed'); }
    finally { setLoading(false); }
  };

  const handleValidate = async () => {
    if (!programmeId || !selectedPipelineId) return;
    setLoading(true); setError(null);
    try { setValidateResult(await apiClient.validateHanaBigQueryPipeline(programmeId, selectedPipelineId, {})); }
    catch (e) { setError(e instanceof APIError ? e.message : 'Validate failed'); }
    finally { setLoading(false); }
  };

  const handleRun = async () => {
    if (!programmeId || !selectedPipelineId) return;
    setLoading(true); setError(null); setInfo(null); setLastRun(null);
    // Animate phases
    let step = 0;
    setAnimPhase(FLOW_PHASES[0]);
    animRef.current = setInterval(() => { step++; if (step < FLOW_PHASES.length) setAnimPhase(FLOW_PHASES[step]); }, 600);
    try {
      const run = await apiClient.startHanaBigQueryRun(programmeId, selectedPipelineId, { row_limit_per_table: rowLimit });
      if (animRef.current) clearInterval(animRef.current);
      setAnimPhase(run.status === 'completed' ? 'completed' : 'failed');
      setLastRun(run);
      setInfo(`Run ${run.id.slice(0, 8)}… — ${run.status}`);
    } catch (e) {
      if (animRef.current) clearInterval(animRef.current);
      setAnimPhase(null);
      setError(e instanceof APIError ? e.message : 'Run failed');
    } finally { setLoading(false); }
  };

  // Mapping helpers
  const updateMapping = (idx: number, patch: Partial<MappingRow>) => setMappings((prev) => prev.map((m, i) => i === idx ? { ...m, ...patch } : m));
  const removeMapping = (idx: number) => setMappings((prev) => prev.filter((_, i) => i !== idx));
  const addMapping = () => setMappings((prev) => [...prev, emptyMapping()]);

  // Stats
  const totalMapped = pipelines.reduce((n, p) => n + p.table_mappings.length, 0);
  const totalRows = lastRun ? lastRun.table_results.reduce((n, t) => n + (t.rows_loaded ?? 0), 0) : 0;
  const runDurationMs = lastRun && lastRun.completed_at ? new Date(lastRun.completed_at).getTime() - new Date(lastRun.started_at).getTime() : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">HANA → BigQuery</h1>
        <p className="mt-1 text-sm text-slate-500">
          Extract SAP HANA tables, stage as CSV, and load into Google BigQuery — full or incremental.
        </p>
      </div>

      {/* Stats dashboard */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        {[
          { label: 'Pipelines', value: pipelines.length, color: 'text-primary-600' },
          { label: 'Tables Mapped', value: totalMapped, color: 'text-accent-600' },
          { label: 'Total Runs', value: runs.length, color: 'text-blue-600' },
          { label: 'Rows Replicated', value: totalRows.toLocaleString(), color: 'text-emerald-600' },
          { label: 'Last Status', value: lastRun?.status ?? '—', color: lastRun?.status === 'completed' ? 'text-emerald-600' : lastRun?.status === 'failed' ? 'text-red-600' : 'text-slate-400' },
        ].map((s) => (
          <div key={s.label} className="stat-card">
            <p className="text-xs text-slate-500">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Alerts */}
      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>}
      {info && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{info}</div>}

      {/* Pipeline flow diagram */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">Pipeline Flow</h2>
        <PipelineFlowDiagram activePhase={animPhase} animating={loading} />
      </div>

      {/* Setup: Discovery + Table Mappings */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Discovery */}
        <div className="card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">Landscape Discovery</h2>
          <p className="text-xs text-slate-400">Connect to SAP to discover the source landscape.</p>
          <button type="button" className="btn-primary w-full" disabled={loading} onClick={handleDiscover}>
            {loading ? 'Discovering...' : 'Run Discovery'}
          </button>
          {landscapeId && (
            <div className="text-xs font-mono bg-slate-50 rounded px-3 py-2 text-slate-600 break-all">
              landscape: {landscapeId.slice(0, 8)}…
            </div>
          )}
        </div>

        {/* Source side — HANA (blue accent) */}
        <div className="card overflow-hidden">
          <div className="px-5 py-3 bg-blue-50 border-b border-blue-100">
            <h2 className="text-sm font-semibold text-blue-800 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" /></svg>
              Source — SAP HANA
            </h2>
          </div>
          <div className="p-5 text-xs text-slate-500">
            <p>{mappings.length} table(s) selected from {new Set(mappings.map((m) => m.sourceSchema)).size} schema(s)</p>
            {mappings.length > 0 && <SchemaPreview table={mappings[0].sourceTable} />}
          </div>
        </div>

        {/* Target side — BigQuery (green accent) */}
        <div className="card overflow-hidden">
          <div className="px-5 py-3 bg-emerald-50 border-b border-emerald-100">
            <h2 className="text-sm font-semibold text-emerald-800 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" /></svg>
              Target — Google BigQuery
            </h2>
          </div>
          <div className="p-5 text-xs text-slate-500">
            <p>{new Set(mappings.map((m) => m.targetDataset)).size} dataset(s): {[...new Set(mappings.map((m) => m.targetDataset))].join(', ')}</p>
            <div className="mt-2 space-y-1">
              {mappings.map((m, i) => (
                <div key={i} className="font-mono text-slate-600">{m.targetDataset}.{m.targetTable}</div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Table mapping builder */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Table Mappings</h2>
          <button type="button" className="btn-secondary text-xs py-1.5 px-3" onClick={addMapping}>
            + Add Table
          </button>
        </div>
        <div className="space-y-2">
          {mappings.map((m, idx) => (
            <div key={idx} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2">
              <select className="input font-mono text-xs py-1.5 flex-1" value={m.sourceSchema} onChange={(e) => { const s = e.target.value; const t = (HANA_CATALOG[s] ?? [])[0] ?? ''; updateMapping(idx, { sourceSchema: s, sourceTable: t, targetTable: suggestBqTable(s, t) }); }}>
                {SCHEMAS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="input font-mono text-xs py-1.5 flex-1" value={m.sourceTable} onChange={(e) => updateMapping(idx, { sourceTable: e.target.value, targetTable: suggestBqTable(m.sourceSchema, e.target.value) })}>
                {(HANA_CATALOG[m.sourceSchema] ?? []).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <svg className="w-5 h-5 text-slate-300 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" /></svg>
              <select className="input font-mono text-xs py-1.5 flex-1" value={m.targetDataset} onChange={(e) => updateMapping(idx, { targetDataset: e.target.value })}>
                {BQ_DATASETS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
              <select className="input font-mono text-xs py-1.5 flex-1" value={m.targetTable} onChange={(e) => updateMapping(idx, { targetTable: e.target.value })}>
                {bqTableOptions(m.sourceSchema, m.sourceTable).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <button type="button" onClick={() => removeMapping(idx)} className="p-1 text-slate-400 hover:text-red-500 transition-colors" title="Remove">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <label className="label">Pipeline name</label>
            <input className="input text-sm" value={pipelineName} onChange={(e) => setPipelineName(e.target.value)} />
          </div>
          <button type="button" className="btn-primary mt-6" disabled={loading || !landscapeId} onClick={handleCreatePipeline}>
            Create Pipeline ({mappings.length} tables)
          </button>
        </div>
      </div>

      {/* Execute */}
      <div className="card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-900">Execute Pipeline</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div className="min-w-[220px] flex-1">
            <label className="label">Pipeline</label>
            <select className="input" value={selectedPipelineId} onChange={(e) => setSelectedPipelineId(e.target.value)}>
              <option value="">— select —</option>
              {pipelines.map((p) => <option key={p.id} value={p.id}>{p.name} — {p.table_mappings.length} table(s)</option>)}
            </select>
          </div>
          <div className="w-28">
            <label className="label">Row limit</label>
            <input type="number" min={1} max={10000} className="input" value={rowLimit} onChange={(e) => setRowLimit(Number(e.target.value) || 10)} />
          </div>
          <button type="button" className="btn-secondary" disabled={loading || !selectedPipelineId} onClick={handleValidate}>
            Validate HANA
          </button>
          <button type="button" className="btn-primary" disabled={loading || !selectedPipelineId} onClick={handleRun}>
            {loading ? (
              <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg> Running...</>
            ) : 'Run Pipeline'}
          </button>
        </div>
        {validateResult && (
          <p className="text-sm"><span className={validateResult.hana_reachable ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'}>{validateResult.hana_reachable ? 'Reachable' : 'Unreachable'}</span> — {validateResult.message}</p>
        )}
      </div>

      {/* Last run — rich result cards */}
      {lastRun && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Run Results</h2>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span className="font-mono">{lastRun.id.slice(0, 12)}…</span>
              <span className={runStatusBadge(lastRun.status)}>{lastRun.status}</span>
              <span>{(runDurationMs / 1000).toFixed(1)}s total</span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {lastRun.table_results.map((t, i) => (
              <TableResultCard key={i} t={t} durationMs={runDurationMs / Math.max(lastRun.table_results.length, 1)} />
            ))}
          </div>
        </div>
      )}

      {/* Recent runs */}
      {runs.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-200 bg-slate-50">
            <h2 className="text-sm font-semibold text-slate-700">Run History</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="table-header">Run ID</th>
                  <th className="table-header">Started</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Tables</th>
                  <th className="table-header">Rows</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.slice(0, 10).map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50 cursor-pointer transition-colors" onClick={() => setLastRun(r)}>
                    <td className="table-cell font-mono text-xs">{r.id.slice(0, 12)}…</td>
                    <td className="table-cell text-slate-500">{new Date(r.started_at).toLocaleString()}</td>
                    <td className="table-cell"><span className={runStatusBadge(r.status)}>{r.status}</span></td>
                    <td className="table-cell">{r.table_results.length}</td>
                    <td className="table-cell font-mono">{r.table_results.reduce((n, t) => n + (t.rows_loaded ?? 0), 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
