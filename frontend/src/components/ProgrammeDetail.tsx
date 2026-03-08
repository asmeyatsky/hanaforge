import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Programme } from '../types';

type Tab = 'overview' | 'discovery' | 'analysis' | 'data' | 'testing';

function statusBadge(status: string) {
  const s = status.toLowerCase();
  if (s.includes('complete') || s === 'completed') return 'badge-green';
  if (s.includes('progress')) return 'badge-blue';
  if (s === 'created') return 'badge-slate';
  return 'badge-amber';
}

function ragColor(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('complete')) return 'bg-emerald-500';
  if (s.includes('progress')) return 'bg-blue-500';
  if (s === 'created') return 'bg-slate-400';
  return 'bg-amber-500';
}

const tabs: { key: Tab; label: string; disabled: boolean }[] = [
  { key: 'overview', label: 'Overview', disabled: false },
  { key: 'discovery', label: 'Discovery', disabled: false },
  { key: 'analysis', label: 'ABAP Analysis', disabled: false },
  { key: 'data', label: 'Data Readiness', disabled: true },
  { key: 'testing', label: 'Testing', disabled: true },
];

export default function ProgrammeDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [programme, setProgramme] = useState<Programme | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const loadProgramme = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const result = await apiClient.getProgramme(id);
      setProgramme(result);
    } catch {
      // Demo fallback
      setProgramme({
        id: id,
        name: 'Acme Corp ECC Migration',
        customer_id: 'ACME-001',
        sap_source_version: 'ECC 6.0',
        target_version: 'S/4HANA 2023',
        status: 'DISCOVERY_COMPLETE',
        complexity_score: {
          score: 67,
          risk_level: 'HIGH',
          benchmark_percentile: 72,
        },
        created_at: '2026-01-15T10:30:00Z',
      });
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadProgramme();
  }, [loadProgramme]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <svg className="animate-spin w-8 h-8 text-primary-600" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (!programme) {
    return (
      <div className="text-center py-32">
        <h2 className="text-lg font-semibold text-slate-900">
          Programme not found
        </h2>
        <button
          onClick={() => navigate('/programmes')}
          className="btn-primary mt-4"
        >
          Back to Programmes
        </button>
      </div>
    );
  }

  const handleTabClick = (tab: Tab) => {
    if (tab === 'discovery') {
      navigate(`/programmes/${id}/discovery`);
    } else if (tab === 'analysis') {
      navigate(`/programmes/${id}/analysis`);
    } else {
      setActiveTab(tab);
    }
  };

  return (
    <div className="space-y-6">
      {/* Programme header */}
      <div className="card p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900">
                {programme.name}
              </h1>
              <span className={statusBadge(programme.status)}>
                {programme.status.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-6 text-sm text-slate-500">
              <span>
                Customer:{' '}
                <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-xs">
                  {programme.customer_id}
                </span>
              </span>
              <span>
                {programme.sap_source_version} &rarr;{' '}
                <span className="font-semibold text-slate-700">
                  {programme.target_version}
                </span>
              </span>
              <span>
                Created:{' '}
                {new Date(programme.created_at).toLocaleDateString('en-GB', {
                  day: '2-digit',
                  month: 'short',
                  year: 'numeric',
                })}
              </span>
            </div>
          </div>
          {programme.complexity_score && (
            <div className="text-center">
              <div
                className={`text-4xl font-black ${
                  programme.complexity_score.score <= 25
                    ? 'text-emerald-600'
                    : programme.complexity_score.score <= 50
                      ? 'text-amber-600'
                      : programme.complexity_score.score <= 75
                        ? 'text-orange-600'
                        : 'text-red-600'
                }`}
              >
                {programme.complexity_score.score}
              </div>
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mt-1">
                {programme.complexity_score.risk_level} Risk
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-0 -mb-px">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => !tab.disabled && handleTabClick(tab.key)}
              disabled={tab.disabled}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key && !tab.disabled
                  ? 'border-primary-600 text-primary-600'
                  : tab.disabled
                    ? 'border-transparent text-slate-300 cursor-not-allowed'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              {tab.label}
              {tab.disabled && (
                <span className="ml-2 text-[10px] bg-slate-100 text-slate-400 px-1.5 py-0.5 rounded-full">
                  Soon
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Key metrics */}
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-3 gap-4">
              <div className="stat-card">
                <p className="text-sm text-slate-500">Custom Objects</p>
                <p className="mt-1 text-2xl font-bold text-slate-900">4,287</p>
                <p className="text-xs text-slate-400 mt-1">Across all packages</p>
              </div>
              <div className="stat-card">
                <p className="text-sm text-slate-500">Integration Points</p>
                <p className="mt-1 text-2xl font-bold text-slate-900">23</p>
                <p className="text-xs text-slate-400 mt-1">RFC, IDoc, API</p>
              </div>
              <div className="stat-card">
                <p className="text-sm text-slate-500">DB Size</p>
                <p className="mt-1 text-2xl font-bold text-slate-900">1.8 TB</p>
                <p className="text-xs text-slate-400 mt-1">Production system</p>
              </div>
            </div>

            {/* Timeline / progress */}
            <div className="card p-6">
              <h3 className="text-sm font-semibold text-slate-900 mb-4">
                Migration Timeline
              </h3>
              <div className="space-y-4">
                {[
                  { phase: 'Discovery', status: 'complete', date: '15 Jan 2026' },
                  { phase: 'ABAP Analysis', status: 'in_progress', date: 'In progress' },
                  { phase: 'Remediation', status: 'pending', date: 'Pending' },
                  { phase: 'Data Readiness', status: 'pending', date: 'Pending' },
                  { phase: 'Testing', status: 'pending', date: 'Pending' },
                  { phase: 'Migration / Cutover', status: 'pending', date: 'Target Q4 2026' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div
                      className={`w-3 h-3 rounded-full flex-shrink-0 ${
                        item.status === 'complete'
                          ? 'bg-emerald-500'
                          : item.status === 'in_progress'
                            ? 'bg-blue-500 animate-pulse'
                            : 'bg-slate-200'
                      }`}
                    />
                    <div className="flex-1 flex items-center justify-between">
                      <span
                        className={`text-sm ${
                          item.status === 'pending'
                            ? 'text-slate-400'
                            : 'text-slate-700 font-medium'
                        }`}
                      >
                        {item.phase}
                      </span>
                      <span className="text-xs text-slate-400">
                        {item.date}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar: health + links */}
          <div className="space-y-6">
            {/* Programme health RAG */}
            <div className="card p-6">
              <h3 className="text-sm font-semibold text-slate-900 mb-4">
                Programme Health
              </h3>
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-4 h-4 rounded-full ${ragColor(programme.status)}`} />
                <span className="text-sm font-medium text-slate-700">
                  {programme.status.includes('PROGRESS')
                    ? 'On Track'
                    : programme.status.includes('COMPLETE')
                      ? 'Phase Complete'
                      : 'Not Started'}
                </span>
              </div>
              <div className="space-y-3">
                {[
                  { label: 'Schedule', rag: 'green' },
                  { label: 'Risk', rag: 'amber' },
                  { label: 'Quality', rag: 'green' },
                  { label: 'Resources', rag: 'green' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">{item.label}</span>
                    <span
                      className={`w-3 h-3 rounded-full ${
                        item.rag === 'green'
                          ? 'bg-emerald-500'
                          : item.rag === 'amber'
                            ? 'bg-amber-500'
                            : 'bg-red-500'
                      }`}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Quick links */}
            <div className="card p-6">
              <h3 className="text-sm font-semibold text-slate-900 mb-4">
                Quick Access
              </h3>
              <div className="space-y-2">
                <button
                  onClick={() => navigate(`/programmes/${id}/discovery`)}
                  className="btn-secondary w-full text-left justify-start"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                  Discovery Panel
                </button>
                <button
                  onClick={() => navigate(`/programmes/${id}/analysis`)}
                  className="btn-secondary w-full text-left justify-start"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
                  </svg>
                  ABAP Analysis
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
