import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { CutoverPlan, RunbookStep } from '../types';

function stepStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-emerald-500';
    case 'in_progress':
      return 'bg-blue-500 animate-pulse';
    case 'failed':
      return 'bg-red-500';
    case 'skipped':
      return 'bg-slate-300';
    default:
      return 'bg-slate-200';
  }
}

function stepBorderColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'border-emerald-500';
    case 'in_progress':
      return 'border-blue-500';
    case 'failed':
      return 'border-red-500';
    default:
      return 'border-slate-200';
  }
}

function goNoGoBadge(status: string) {
  switch (status) {
    case 'go':
      return 'badge-green';
    case 'no_go':
      return 'badge-red';
    default:
      return 'badge-slate';
  }
}

function incidentSeverityBadge(severity: string) {
  switch (severity) {
    case 'P1':
      return 'badge-red';
    case 'P2':
      return 'badge-amber';
    case 'P3':
      return 'badge-blue';
    default:
      return 'badge-slate';
  }
}

function incidentStatusBadge(status: string) {
  switch (status) {
    case 'open':
      return 'badge-red';
    case 'investigating':
      return 'badge-amber';
    case 'resolved':
      return 'badge-green';
    case 'closed':
      return 'badge-slate';
    default:
      return 'badge-slate';
  }
}

const POLL_INTERVAL_MS = 5000;

export default function CutoverPanel() {
  const { id: programmeId } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<CutoverPlan | null>(null);
  const [updatingTask, setUpdatingTask] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Determine if cutover is active (should poll)
  const isActive = plan?.status === 'executing';

  const fetchStatus = useCallback(async () => {
    if (!programmeId) return;
    try {
      const data = await apiClient.getCutoverStatus(programmeId);
      setPlan(data);
      setError(null);
    } catch {
      // Only set error if we don't already have data (initial load)
      if (!plan) {
        setError(null); // Silently fail on poll, keep existing data
      }
    }
  }, [programmeId, plan]);

  // Auto-poll during active cutover
  useEffect(() => {
    if (isActive) {
      pollRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [isActive, fetchStatus]);

  const handleGenerateRunbook = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.generateRunbook(programmeId);
      setPlan(data);
    } catch {
      setError('Failed to generate runbook. Check that the programme exists and has discovery data.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartCutover = async () => {
    if (!programmeId || !plan) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.startCutover(plan.plan_id);
      setPlan(data);
    } catch {
      setError('Failed to start cutover. Ensure all Go/No-Go gates are cleared and the runbook is approved.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartHypercare = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.startHypercare(programmeId);
      setPlan(data);
    } catch {
      setError('Failed to start hypercare. Complete cutover first.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadExisting = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getCutoverStatus(programmeId);
      setPlan(data);
    } catch {
      setError('No existing cutover plan found. Generate a runbook to get started.');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await fetchStatus();
  };

  const handleUpdateTask = async (step: RunbookStep, newStatus: string) => {
    if (!plan) return;
    setUpdatingTask(step.id);
    try {
      const data = await apiClient.updateCutoverTask(
        plan.plan_id,
        step.id,
        newStatus,
      );
      setPlan(data);
      setError(null);
    } catch {
      setError(`Failed to update task "${step.name}" to ${newStatus}.`);
    } finally {
      setUpdatingTask(null);
    }
  };

  const completedSteps = plan ? plan.runbook_steps.filter((s) => s.status === 'completed').length : 0;
  const totalSteps = plan ? plan.runbook_steps.length : 0;
  const totalEstimatedMin = plan ? plan.runbook_steps.reduce((sum, s) => sum + s.estimated_duration_min, 0) : 0;
  const totalActualMin = plan ? plan.runbook_steps.reduce((sum, s) => sum + (s.actual_duration_min || 0), 0) : 0;
  const progressPercent = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

  const goCount = plan ? plan.go_no_go_gates.filter((g) => g.status === 'go').length : 0;
  const noGoCount = plan ? plan.go_no_go_gates.filter((g) => g.status === 'no_go').length : 0;

  const activeIncidents = plan ? plan.incidents.filter((i) => i.status === 'open' || i.status === 'investigating').length : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Cutover & Hypercare
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage your cutover runbook, Go/No-Go gates, and post-go-live hypercare operations.
          </p>
          {isActive && (
            <p className="mt-1 text-xs text-blue-600 flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              Live — auto-refreshing every {POLL_INTERVAL_MS / 1000}s
            </p>
          )}
        </div>
        <div className="flex gap-3">
          {plan && (
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="btn-secondary disabled:opacity-50"
              title="Refresh status"
            >
              <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          )}
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
              onClick={handleGenerateRunbook}
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
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
                  </svg>
                  Generate Runbook
                </>
              )}
            </button>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={handleStartCutover}
                disabled={loading || plan.status === 'executing' || plan.status === 'cutover_complete' || plan.status === 'hypercare'}
                className="btn-primary disabled:opacity-50"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                </svg>
                Start Cutover
              </button>
              <button
                onClick={handleStartHypercare}
                disabled={loading || plan.status === 'hypercare' || plan.status === 'planning' || plan.status === 'ready'}
                className="btn-accent disabled:opacity-50"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                </svg>
                Start Hypercare
              </button>
            </div>
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
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
          </svg>
          <h3 className="mt-4 text-base font-medium text-slate-500">
            No cutover plan yet
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Generate a runbook to plan your cutover steps, timing, and Go/No-Go gates.
          </p>
        </div>
      )}

      {/* Plan results */}
      {plan && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
            <div className="stat-card">
              <p className="text-sm text-slate-500">Status</p>
              <p className="mt-1 text-lg font-bold text-slate-900 uppercase">
                {plan.status.replace('_', ' ')}
              </p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Cutover Progress</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {progressPercent}%
              </p>
              <p className="text-xs text-slate-400 mt-1">{completedSteps}/{totalSteps} steps</p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Est. Total Time</p>
              <p className="mt-1 text-3xl font-bold text-slate-900">
                {Math.floor(totalEstimatedMin / 60)}h {totalEstimatedMin % 60}m
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Actual so far: {Math.floor(totalActualMin / 60)}h {totalActualMin % 60}m
              </p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Go/No-Go</p>
              <div className="mt-2 flex items-center gap-3">
                <span className="text-lg font-bold text-emerald-600">{goCount} Go</span>
                {noGoCount > 0 && (
                  <span className="text-lg font-bold text-red-600">{noGoCount} No-Go</span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {plan.go_no_go_gates.filter((g) => g.status === 'pending').length} pending
              </p>
            </div>
            <div className="stat-card">
              <p className="text-sm text-slate-500">Incidents</p>
              <p className={`mt-1 text-3xl font-bold ${activeIncidents > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                {activeIncidents}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                active / {plan.incidents.length} total
              </p>
            </div>
          </div>

          {/* Overall progress bar */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-700">Overall Progress</span>
              <span className="text-sm font-mono text-slate-500">{progressPercent}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-3">
              <div
                className="bg-emerald-500 h-3 rounded-full transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Cutover stepper */}
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-6">
              Cutover Execution Progress
            </h3>
            <div className="relative">
              {/* Progress line */}
              <div className="absolute top-4 left-4 right-4 h-0.5 bg-slate-200" />
              <div
                className="absolute top-4 left-4 h-0.5 bg-emerald-500 transition-all duration-500"
                style={{
                  width: totalSteps > 1
                    ? `${(completedSteps / (totalSteps - 1)) * 100}%`
                    : '0%',
                  maxWidth: 'calc(100% - 2rem)',
                }}
              />

              {/* Steps */}
              <div className="relative flex justify-between">
                {plan.runbook_steps.map((step) => (
                  <div key={step.id} className="flex flex-col items-center" style={{ width: `${100 / totalSteps}%` }}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 bg-white z-10 ${stepBorderColor(step.status)}`}>
                      {step.status === 'completed' ? (
                        <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      ) : step.status === 'in_progress' ? (
                        <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
                      ) : step.status === 'failed' ? (
                        <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      ) : (
                        <span className="text-[10px] font-bold text-slate-400">{step.order}</span>
                      )}
                    </div>
                    <p className="mt-2 text-[10px] text-slate-500 text-center leading-tight max-w-[80px] truncate" title={step.name}>
                      {step.name}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Runbook steps table with task actions */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-900">
                Runbook Steps
              </h3>
            </div>
            <div className="divide-y divide-slate-100">
              {plan.runbook_steps.map((step) => (
                <div key={step.id} className="px-6 py-4 flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full flex-shrink-0 ${stepStatusColor(step.status)}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-slate-400">#{step.order}</span>
                      <span className="text-sm font-semibold text-slate-900">{step.name}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">{step.description}</p>
                  </div>
                  <div className="flex items-center gap-4 flex-shrink-0">
                    <div className="text-right">
                      <p className="text-xs text-slate-400">Owner</p>
                      <p className="text-xs font-medium text-slate-700">{step.owner}</p>
                    </div>
                    <div className="text-right min-w-[80px]">
                      <p className="text-xs text-slate-400">Duration</p>
                      <p className="text-xs font-mono text-slate-700">
                        {step.actual_duration_min !== null
                          ? `${step.actual_duration_min}m (est. ${step.estimated_duration_min}m)`
                          : `est. ${step.estimated_duration_min}m`}
                      </p>
                    </div>
                    {/* Task action buttons */}
                    {isActive && (
                      <div className="flex gap-1 min-w-[120px] justify-end">
                        {step.status === 'pending' && (
                          <button
                            onClick={() => handleUpdateTask(step, 'IN_PROGRESS')}
                            disabled={updatingTask === step.id}
                            className="px-2 py-1 text-[10px] font-medium rounded bg-blue-100 text-blue-700 hover:bg-blue-200 disabled:opacity-50"
                          >
                            {updatingTask === step.id ? '...' : 'Start'}
                          </button>
                        )}
                        {step.status === 'in_progress' && (
                          <>
                            <button
                              onClick={() => handleUpdateTask(step, 'COMPLETED')}
                              disabled={updatingTask === step.id}
                              className="px-2 py-1 text-[10px] font-medium rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200 disabled:opacity-50"
                            >
                              {updatingTask === step.id ? '...' : 'Complete'}
                            </button>
                            <button
                              onClick={() => handleUpdateTask(step, 'FAILED')}
                              disabled={updatingTask === step.id}
                              className="px-2 py-1 text-[10px] font-medium rounded bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-50"
                            >
                              Fail
                            </button>
                          </>
                        )}
                        {step.status === 'failed' && (
                          <button
                            onClick={() => handleUpdateTask(step, 'IN_PROGRESS')}
                            disabled={updatingTask === step.id}
                            className="px-2 py-1 text-[10px] font-medium rounded bg-amber-100 text-amber-700 hover:bg-amber-200 disabled:opacity-50"
                          >
                            {updatingTask === step.id ? '...' : 'Retry'}
                          </button>
                        )}
                        {step.status === 'completed' && (
                          <span className="px-2 py-1 text-[10px] font-medium text-emerald-600">Done</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Go/No-Go gates */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-sm font-semibold text-slate-900">
                Go/No-Go Gates
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="table-header">Gate</th>
                    <th className="table-header">Category</th>
                    <th className="table-header">Status</th>
                    <th className="table-header">Checked By</th>
                    <th className="table-header">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {plan.go_no_go_gates.map((gate) => (
                    <tr key={gate.id} className="hover:bg-slate-50 transition-colors">
                      <td className="table-cell text-sm font-semibold text-slate-900">{gate.name}</td>
                      <td className="table-cell">
                        <span className="badge-slate">{gate.category}</span>
                      </td>
                      <td className="table-cell">
                        <span className={goNoGoBadge(gate.status)}>
                          {gate.status === 'go' ? 'GO' : gate.status === 'no_go' ? 'NO-GO' : 'Pending'}
                        </span>
                      </td>
                      <td className="table-cell text-sm text-slate-600">
                        {gate.checked_by || '--'}
                      </td>
                      <td className="table-cell text-xs text-slate-400">
                        {gate.checked_at
                          ? new Date(gate.checked_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
                          : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Hypercare incidents */}
          {plan.incidents.length > 0 && (
            <div className="card overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
                <h3 className="text-sm font-semibold text-slate-900">
                  Hypercare Incidents ({plan.incidents.length})
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="table-header">Severity</th>
                      <th className="table-header">Title</th>
                      <th className="table-header">Status</th>
                      <th className="table-header">Assignee</th>
                      <th className="table-header">Reported</th>
                      <th className="table-header">Resolved</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {plan.incidents.map((incident) => (
                      <tr key={incident.id} className="hover:bg-slate-50 transition-colors">
                        <td className="table-cell">
                          <span className={incidentSeverityBadge(incident.severity)}>
                            {incident.severity}
                          </span>
                        </td>
                        <td className="table-cell text-sm text-slate-900 max-w-xs">
                          {incident.title}
                        </td>
                        <td className="table-cell">
                          <span className={incidentStatusBadge(incident.status)}>
                            {incident.status}
                          </span>
                        </td>
                        <td className="table-cell text-sm text-slate-600">
                          {incident.assignee}
                        </td>
                        <td className="table-cell text-xs text-slate-400">
                          {new Date(incident.reported_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="table-cell text-xs text-slate-400">
                          {incident.resolved_at
                            ? new Date(incident.resolved_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
                            : '--'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Timing information */}
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Timeline</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-slate-400">Cutover Start</p>
                <p className="font-medium text-slate-700">
                  {plan.cutover_start
                    ? new Date(plan.cutover_start).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : 'Not started'}
                </p>
              </div>
              <div>
                <p className="text-slate-400">Cutover End</p>
                <p className="font-medium text-slate-700">
                  {plan.cutover_end
                    ? new Date(plan.cutover_end).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : 'In progress'}
                </p>
              </div>
              <div>
                <p className="text-slate-400">Hypercare Start</p>
                <p className="font-medium text-slate-700">
                  {plan.hypercare_start
                    ? new Date(plan.hypercare_start).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : '--'}
                </p>
              </div>
              <div>
                <p className="text-slate-400">Hypercare End</p>
                <p className="font-medium text-slate-700">
                  {plan.hypercare_end
                    ? new Date(plan.hypercare_end).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : '--'}
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
