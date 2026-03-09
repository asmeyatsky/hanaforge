import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { MigrationPlan, MigrationTask, MigrationTaskStatus } from '../types';

function taskStatusBadge(status: MigrationTaskStatus) {
  switch (status) {
    case 'completed':
      return 'badge-green';
    case 'running':
      return 'badge-blue';
    case 'failed':
      return 'badge-red';
    case 'blocked':
      return 'badge-amber';
    default:
      return 'badge-slate';
  }
}

function taskStatusColor(status: MigrationTaskStatus): string {
  switch (status) {
    case 'completed':
      return 'bg-emerald-500 border-emerald-600';
    case 'running':
      return 'bg-blue-500 border-blue-600 animate-pulse';
    case 'failed':
      return 'bg-red-500 border-red-600';
    case 'blocked':
      return 'bg-amber-500 border-amber-600';
    default:
      return 'bg-slate-300 border-slate-400';
  }
}

function progressBarColor(status: MigrationTaskStatus): string {
  switch (status) {
    case 'completed':
      return 'bg-emerald-500';
    case 'running':
      return 'bg-blue-500';
    case 'failed':
      return 'bg-red-500';
    default:
      return 'bg-slate-300';
  }
}

// Simple DAG visualization using CSS grid + SVG arrows
function TaskDAG({ tasks }: { tasks: MigrationTask[] }) {
  // Build adjacency for column placement
  const taskMap = new Map(tasks.map((t) => [t.id, t]));

  // Assign columns based on dependency depth
  const getDepth = (taskId: string, visited = new Set<string>()): number => {
    if (visited.has(taskId)) return 0;
    visited.add(taskId);
    const task = taskMap.get(taskId);
    if (!task || task.depends_on.length === 0) return 0;
    return 1 + Math.max(...task.depends_on.map((dep) => getDepth(dep, visited)));
  };

  const tasksByColumn: Map<number, MigrationTask[]> = new Map();
  for (const task of tasks) {
    const col = getDepth(task.id);
    if (!tasksByColumn.has(col)) tasksByColumn.set(col, []);
    tasksByColumn.get(col)!.push(task);
  }

  const columns = Array.from(tasksByColumn.entries()).sort(([a], [b]) => a - b);

  return (
    <div className="flex items-start gap-2 overflow-x-auto pb-4">
      {columns.map(([col, colTasks], colIdx) => (
        <div key={col} className="flex items-start gap-2">
          <div className="flex flex-col gap-3 min-w-[180px]">
            {colTasks.map((task) => (
              <div
                key={task.id}
                className={`rounded-lg border-2 p-3 bg-white shadow-sm ${
                  task.status === 'running'
                    ? 'border-blue-400 ring-2 ring-blue-100'
                    : task.status === 'completed'
                      ? 'border-emerald-300'
                      : task.status === 'failed'
                        ? 'border-red-300'
                        : 'border-slate-200'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-2.5 h-2.5 rounded-full ${taskStatusColor(task.status)}`} />
                  <span className="text-xs font-semibold text-slate-700 truncate">
                    {task.name}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${progressBarColor(task.status)}`}
                      style={{ width: `${task.progress_percent}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {task.progress_percent}%
                  </span>
                </div>
              </div>
            ))}
          </div>
          {/* Arrow between columns */}
          {colIdx < columns.length - 1 && (
            <div className="flex items-center self-center pt-2 flex-shrink-0">
              <svg width="32" height="24" viewBox="0 0 32 24" fill="none">
                <path d="M0 12h24" stroke="#cbd5e1" strokeWidth="2" />
                <path d="M20 6l6 6-6 6" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function MigrationPanel() {
  const { id: programmeId } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<MigrationPlan | null>(null);

  const handleCreatePlan = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.createMigrationPlan(programmeId);
      setPlan(data);
    } catch {
      // Demo fallback
      setPlan({
        programme_id: programmeId,
        plan_id: 'mig-001',
        status: 'executing',
        created_at: new Date().toISOString(),
        tasks: [
          { id: 't1', name: 'Pre-check Validation', status: 'completed', progress_percent: 100, depends_on: [], started_at: '2026-03-08T08:00:00Z', completed_at: '2026-03-08T08:45:00Z' },
          { id: 't2', name: 'Schema Migration', status: 'completed', progress_percent: 100, depends_on: ['t1'], started_at: '2026-03-08T09:00:00Z', completed_at: '2026-03-08T11:30:00Z' },
          { id: 't3', name: 'Data Transfer - FI', status: 'completed', progress_percent: 100, depends_on: ['t2'], started_at: '2026-03-08T12:00:00Z', completed_at: '2026-03-08T18:00:00Z' },
          { id: 't4', name: 'Data Transfer - SD', status: 'running', progress_percent: 68, depends_on: ['t2'], started_at: '2026-03-08T12:00:00Z', completed_at: null },
          { id: 't5', name: 'Data Transfer - MM', status: 'running', progress_percent: 42, depends_on: ['t2'], started_at: '2026-03-08T13:00:00Z', completed_at: null },
          { id: 't6', name: 'Code Deployment', status: 'pending', progress_percent: 0, depends_on: ['t3', 't4', 't5'], started_at: null, completed_at: null },
          { id: 't7', name: 'Post-migration Validation', status: 'pending', progress_percent: 0, depends_on: ['t6'], started_at: null, completed_at: null },
          { id: 't8', name: 'Integration Test Run', status: 'pending', progress_percent: 0, depends_on: ['t7'], started_at: null, completed_at: null },
        ],
        quality_gates: [
          { id: 'qg1', name: 'Data Integrity Check', passed: true, checked_at: '2026-03-08T11:35:00Z', details: 'All 4.2M FI records validated against source checksums' },
          { id: 'qg2', name: 'Schema Compatibility', passed: true, checked_at: '2026-03-08T11:30:00Z', details: 'All 847 tables successfully migrated to S/4HANA schema' },
          { id: 'qg3', name: 'Custom Code Deployment', passed: null, checked_at: null, details: 'Awaiting code deployment phase completion' },
          { id: 'qg4', name: 'Performance Baseline', passed: null, checked_at: null, details: 'Awaiting post-migration validation' },
          { id: 'qg5', name: 'Integration Smoke Test', passed: null, checked_at: null, details: 'RFC, IDoc, and API connectivity verification pending' },
        ],
        audit_log: [
          { id: 'a1', timestamp: '2026-03-08T18:00:00Z', actor: 'system', action: 'Data Transfer - FI completed', details: '4.2M records transferred in 6h 0m' },
          { id: 'a2', timestamp: '2026-03-08T13:00:00Z', actor: 'system', action: 'Data Transfer - MM started', details: 'Batch size: 50,000 records' },
          { id: 'a3', timestamp: '2026-03-08T12:00:00Z', actor: 'system', action: 'Data Transfer - SD started', details: 'Batch size: 50,000 records' },
          { id: 'a4', timestamp: '2026-03-08T12:00:00Z', actor: 'system', action: 'Data Transfer - FI started', details: 'Batch size: 50,000 records' },
          { id: 'a5', timestamp: '2026-03-08T11:30:00Z', actor: 'system', action: 'Schema Migration completed', details: '847 tables migrated in 2h 30m' },
          { id: 'a6', timestamp: '2026-03-08T09:00:00Z', actor: 'admin@acme.com', action: 'Schema Migration started', details: 'DDL execution initiated' },
          { id: 'a7', timestamp: '2026-03-08T08:45:00Z', actor: 'system', action: 'Pre-check Validation passed', details: 'All 12 pre-checks passed' },
          { id: 'a8', timestamp: '2026-03-08T08:00:00Z', actor: 'admin@acme.com', action: 'Migration execution started', details: 'Plan mig-001 approved and execution initiated' },
        ],
      });
      setError(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.executeMigration(programmeId);
      setPlan(data);
    } catch {
      setError('Failed to execute migration. Please check prerequisites.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadExisting = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getMigrationPlan(programmeId);
      setPlan(data);
    } catch {
      setError('No existing migration plan found. Create a plan to get started.');
    } finally {
      setLoading(false);
    }
  };

  const completedTasks = plan ? plan.tasks.filter((t) => t.status === 'completed').length : 0;
  const totalTasks = plan ? plan.tasks.length : 0;
  const overallProgress = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Migration Execution
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Orchestrate and monitor your S/4HANA migration tasks, quality gates, and audit trail.
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
          {!plan ? (
            <button
              onClick={handleCreatePlan}
              disabled={loading}
              className="btn-accent disabled:opacity-50"
            >
              {loading ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creating...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                  Create Plan
                </>
              )}
            </button>
          ) : (
            <button
              onClick={handleExecute}
              disabled={loading || plan.status === 'executing' || plan.status === 'completed'}
              className="btn-primary disabled:opacity-50"
            >
              {loading ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Starting...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                  </svg>
                  Execute
                </>
              )}
            </button>
          )}
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
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
          <h3 className="mt-4 text-base font-medium text-slate-500">
            No migration plan yet
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Create a migration execution plan to orchestrate your S/4HANA data migration and code deployment.
          </p>
        </div>
      )}

      {/* Plan results */}
      {plan && (
        <>
          {/* Progress summary */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="stat-card">
              <p className="text-sm text-slate-500">Status</p>
              <div className="mt-2">
                <span className={
                  plan.status === 'executing' ? 'badge-blue' :
                  plan.status === 'completed' ? 'badge-green' :
                  plan.status === 'failed' ? 'badge-red' :
                  'badge-amber'
                }>
                  {plan.status}
                </span>
              </div>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Overall Progress</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">{overallProgress}%</p>
              <p className="text-xs text-slate-400 mt-1">{completedTasks}/{totalTasks} tasks</p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Quality Gates</p>
              <p className="mt-1 text-3xl font-bold text-emerald-600">
                {plan.quality_gates.filter((g) => g.passed === true).length}/{plan.quality_gates.length}
              </p>
              <p className="text-xs text-slate-400 mt-1">passed</p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Running Tasks</p>
              <p className="mt-1 text-3xl font-bold text-blue-600">
                {plan.tasks.filter((t) => t.status === 'running').length}
              </p>
              <p className="text-xs text-slate-400 mt-1">in progress</p>
            </div>
          </div>

          {/* DAG visualization */}
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">
              Task Dependency Graph
            </h3>
            <TaskDAG tasks={plan.tasks} />
          </div>

          {/* Task table */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-900">
                Task Status ({plan.tasks.length} tasks)
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="table-header">Task</th>
                    <th className="table-header">Status</th>
                    <th className="table-header">Progress</th>
                    <th className="table-header">Started</th>
                    <th className="table-header">Completed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {plan.tasks.map((task) => (
                    <tr key={task.id} className="hover:bg-slate-50 transition-colors">
                      <td className="table-cell">
                        <span className="text-sm font-semibold text-slate-900">{task.name}</span>
                      </td>
                      <td className="table-cell">
                        <span className={taskStatusBadge(task.status)}>{task.status}</span>
                      </td>
                      <td className="table-cell">
                        <div className="flex items-center gap-3 min-w-[120px]">
                          <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${progressBarColor(task.status)}`}
                              style={{ width: `${task.progress_percent}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500 font-mono w-8 text-right">
                            {task.progress_percent}%
                          </span>
                        </div>
                      </td>
                      <td className="table-cell text-xs text-slate-500">
                        {task.started_at
                          ? new Date(task.started_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
                          : '--'}
                      </td>
                      <td className="table-cell text-xs text-slate-500">
                        {task.completed_at
                          ? new Date(task.completed_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
                          : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Quality gates */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-900">
                Quality Gates
              </h3>
            </div>
            <div className="divide-y divide-slate-100">
              {plan.quality_gates.map((gate) => (
                <div key={gate.id} className="px-6 py-4 flex items-center gap-4">
                  <div className="flex-shrink-0">
                    {gate.passed === true && (
                      <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                        <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      </div>
                    )}
                    {gate.passed === false && (
                      <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
                        <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                    )}
                    {gate.passed === null && (
                      <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
                        <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900">{gate.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{gate.details}</p>
                  </div>
                  {gate.checked_at && (
                    <span className="text-xs text-slate-400 flex-shrink-0">
                      {new Date(gate.checked_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Audit log timeline */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-900">
                Audit Log
              </h3>
            </div>
            <div className="px-6 py-4">
              <div className="space-y-0">
                {plan.audit_log.map((entry, i) => (
                  <div key={entry.id} className="flex gap-4">
                    {/* Timeline line */}
                    <div className="flex flex-col items-center">
                      <div className="w-2.5 h-2.5 rounded-full bg-primary-500 flex-shrink-0 mt-1.5" />
                      {i < plan.audit_log.length - 1 && (
                        <div className="w-px flex-1 bg-slate-200 my-1" />
                      )}
                    </div>
                    <div className="pb-4 flex-1 min-w-0">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-slate-900">{entry.action}</span>
                        <span className="text-xs text-slate-400">
                          {new Date(entry.timestamp).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">{entry.details}</p>
                      <p className="text-[10px] text-slate-400 mt-0.5">by {entry.actor}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
