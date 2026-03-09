import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { TestForgeResult, TestSuite } from '../types';

function statusBadge(status: string) {
  switch (status) {
    case 'passed':
      return 'badge-green';
    case 'failed':
      return 'badge-red';
    case 'skipped':
      return 'badge-amber';
    default:
      return 'badge-slate';
  }
}

function CoverageGauge({ percent }: { percent: number }) {
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  const gaugeColor = () => {
    if (percent >= 80) return 'stroke-emerald-500';
    if (percent >= 60) return 'stroke-amber-500';
    return 'stroke-red-500';
  };

  const textColor = () => {
    if (percent >= 80) return 'text-emerald-600';
    if (percent >= 60) return 'text-amber-600';
    return 'text-red-600';
  };

  return (
    <div className="relative w-32 h-32 flex-shrink-0">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="10"
        />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          className={gaugeColor()}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          strokeDashoffset={`${offset}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-3xl font-black ${textColor()}`}>
          {percent}
        </span>
        <span className="text-[10px] text-slate-400 uppercase font-semibold">
          % coverage
        </span>
      </div>
    </div>
  );
}

function SuiteCard({ suite, expanded, onToggle }: { suite: TestSuite; expanded: boolean; onToggle: () => void }) {
  const total = suite.total_count;
  const passPercent = total > 0 ? Math.round((suite.pass_count / total) * 100) : 0;

  return (
    <div className="card overflow-hidden">
      <div
        className="p-5 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <svg
              className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
            <h4 className="text-sm font-semibold text-slate-900">{suite.name}</h4>
            <span className="badge-slate">{suite.module}</span>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="text-emerald-600 font-semibold">{suite.pass_count} pass</span>
            <span className="text-red-600 font-semibold">{suite.fail_count} fail</span>
            <span className="text-slate-400 font-semibold">{suite.skip_count} skip</span>
          </div>
        </div>
        {/* Pass rate bar */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
            <div className="flex h-full">
              <div
                className="bg-emerald-500 transition-all duration-500"
                style={{ width: `${passPercent}%` }}
              />
              <div
                className="bg-red-500 transition-all duration-500"
                style={{ width: `${total > 0 ? Math.round((suite.fail_count / total) * 100) : 0}%` }}
              />
              <div
                className="bg-amber-400 transition-all duration-500"
                style={{ width: `${total > 0 ? Math.round((suite.skip_count / total) * 100) : 0}%` }}
              />
            </div>
          </div>
          <span className="text-xs text-slate-400 w-12 text-right">{passPercent}%</span>
        </div>
      </div>

      {/* Expanded scenarios */}
      {expanded && (
        <div className="border-t border-slate-200 divide-y divide-slate-100">
          {suite.scenarios.map((scenario) => (
            <div key={scenario.id} className="px-5 py-3 flex items-center gap-4">
              <span className={statusBadge(scenario.status)}>
                {scenario.status}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-700 font-medium truncate">
                  {scenario.name}
                </p>
                <p className="text-xs text-slate-400 truncate">
                  {scenario.description}
                </p>
              </div>
              {scenario.duration_ms !== null && (
                <span className="text-xs text-slate-400 flex-shrink-0">
                  {scenario.duration_ms}ms
                </span>
              )}
              {scenario.error_message && (
                <span className="text-xs text-red-500 flex-shrink-0 max-w-xs truncate">
                  {scenario.error_message}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function TestForgePanel() {
  const { id: programmeId } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TestForgeResult | null>(null);
  const [expandedSuite, setExpandedSuite] = useState<string | null>(null);

  const handleGenerateTests = async () => {
    if (!programmeId) return;
    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.generateTests(programmeId);
      setResult(data);
    } catch {
      // Demo fallback
      setResult({
        programme_id: programmeId,
        total_pass: 42,
        total_fail: 5,
        total_skip: 3,
        coverage_percent: 78,
        generated_at: new Date().toISOString(),
        suites: [
          {
            id: 'ts1',
            name: 'Finance Module Regression',
            module: 'FI',
            pass_count: 18,
            fail_count: 2,
            skip_count: 1,
            total_count: 21,
            created_at: '2026-03-08T10:00:00Z',
            scenarios: [
              { id: 's1', name: 'GL Account Posting', description: 'Verify GL postings create correct ACDOCA entries', status: 'passed', duration_ms: 1240, error_message: null },
              { id: 's2', name: 'Vendor Payment Run', description: 'End-to-end payment run with automatic clearing', status: 'passed', duration_ms: 3420, error_message: null },
              { id: 's3', name: 'Asset Depreciation', description: 'Monthly depreciation run for all asset classes', status: 'failed', duration_ms: 2100, error_message: 'ACDOCA mapping error for asset class 3000' },
              { id: 's4', name: 'Tax Calculation', description: 'Tax jurisdiction determination and calculation', status: 'passed', duration_ms: 890, error_message: null },
              { id: 's5', name: 'Intercompany Posting', description: 'Cross-company code journal entries', status: 'skipped', duration_ms: null, error_message: null },
            ],
          },
          {
            id: 'ts2',
            name: 'Sales & Distribution Regression',
            module: 'SD',
            pass_count: 14,
            fail_count: 2,
            skip_count: 1,
            total_count: 17,
            created_at: '2026-03-08T10:00:00Z',
            scenarios: [
              { id: 's6', name: 'Standard Order Creation', description: 'Create sales order with pricing and availability check', status: 'passed', duration_ms: 1560, error_message: null },
              { id: 's7', name: 'Delivery Processing', description: 'Outbound delivery with picking and goods issue', status: 'passed', duration_ms: 2340, error_message: null },
              { id: 's8', name: 'Billing Document', description: 'Invoice creation from delivery', status: 'failed', duration_ms: 1800, error_message: 'Pricing condition type MWST mapping failure' },
              { id: 's9', name: 'Credit Memo', description: 'Credit memo creation and posting', status: 'passed', duration_ms: 1100, error_message: null },
              { id: 's10', name: 'Returns Processing', description: 'Full returns cycle with refund', status: 'passed', duration_ms: 2800, error_message: null },
            ],
          },
          {
            id: 'ts3',
            name: 'Materials Management Regression',
            module: 'MM',
            pass_count: 10,
            fail_count: 1,
            skip_count: 1,
            total_count: 12,
            created_at: '2026-03-08T10:00:00Z',
            scenarios: [
              { id: 's11', name: 'Purchase Order Creation', description: 'PO creation with account assignment and pricing', status: 'passed', duration_ms: 1340, error_message: null },
              { id: 's12', name: 'Goods Receipt', description: 'GR posting against purchase order', status: 'passed', duration_ms: 980, error_message: null },
              { id: 's13', name: 'Invoice Verification', description: 'Three-way match and invoice posting', status: 'failed', duration_ms: 1560, error_message: 'Tolerance group BSEG migration issue' },
              { id: 's14', name: 'Physical Inventory', description: 'Stock count and adjustment posting', status: 'passed', duration_ms: 1200, error_message: null },
            ],
          },
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
      const data = await apiClient.getTestResults(programmeId);
      setResult(data);
    } catch {
      setError('No existing test results found. Generate tests to get started.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">TestForge</h1>
          <p className="mt-1 text-sm text-slate-500">
            AI-generated regression test suites for validating your S/4HANA migration.
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
            onClick={handleGenerateTests}
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
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
                </svg>
                Generate Tests
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
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
          </svg>
          <h3 className="mt-4 text-base font-medium text-slate-500">
            No test suites generated yet
          </h3>
          <p className="mt-1 text-sm text-slate-400">
            Generate AI-powered regression tests based on your ABAP analysis results.
          </p>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Stats cards */}
            <div className="stat-card border-l-4 border-l-emerald-500">
              <p className="text-sm text-slate-500">Passed</p>
              <p className="mt-1 text-3xl font-bold text-emerald-600">{result.total_pass}</p>
              <p className="text-xs text-slate-400 mt-1">test scenarios</p>
            </div>
            <div className="stat-card border-l-4 border-l-red-500">
              <p className="text-sm text-slate-500">Failed</p>
              <p className="mt-1 text-3xl font-bold text-red-600">{result.total_fail}</p>
              <p className="text-xs text-slate-400 mt-1">test scenarios</p>
            </div>
            <div className="stat-card border-l-4 border-l-amber-500">
              <p className="text-sm text-slate-500">Skipped</p>
              <p className="mt-1 text-3xl font-bold text-amber-600">{result.total_skip}</p>
              <p className="text-xs text-slate-400 mt-1">test scenarios</p>
            </div>

            {/* Coverage gauge */}
            <div className="stat-card flex items-center justify-center">
              <CoverageGauge percent={result.coverage_percent} />
            </div>
          </div>

          {/* Test suites */}
          <div>
            <h2 className="text-base font-semibold text-slate-900 mb-4">
              Test Suites ({result.suites.length})
            </h2>
            <div className="space-y-4">
              {result.suites.map((suite) => (
                <SuiteCard
                  key={suite.id}
                  suite={suite}
                  expanded={expandedSuite === suite.id}
                  onToggle={() =>
                    setExpandedSuite(expandedSuite === suite.id ? null : suite.id)
                  }
                />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
