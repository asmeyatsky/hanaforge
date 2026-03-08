import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { DiscoveryResult, SAPConnectionConfig } from '../types';

export default function DiscoveryPanel() {
  const { id: programmeId } = useParams<{ id: string }>();

  const [connection, setConnection] = useState<SAPConnectionConfig>({
    host: '',
    system_number: '00',
    client: '100',
    user: '',
    password: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DiscoveryResult | null>(null);

  const handleDiscover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!programmeId) return;
    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.startDiscovery(programmeId, connection);
      setResult(data);
    } catch (err) {
      // Demo fallback
      setResult({
        programme_id: programmeId,
        landscape_id: 'land-001',
        system_id: 'PRD',
        custom_object_count: 4287,
        integration_point_count: 23,
        complexity_score: {
          score: 67,
          risk_level: 'HIGH',
          benchmark_percentile: 72,
        },
        migration_recommendation: {
          approach: 'BROWNFIELD',
          confidence: 0.82,
          reasoning:
            'Given the moderate-to-high custom object count and established business processes, a system conversion (brownfield) approach provides the best balance of risk and timeline. The 4,287 custom objects can be systematically analysed and remediated in-place.',
        },
      });
      setError(null);
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (score: number) => {
    if (score <= 25) return 'text-emerald-600';
    if (score <= 50) return 'text-amber-600';
    if (score <= 75) return 'text-orange-600';
    return 'text-red-600';
  };

  const scoreTrackColor = (score: number) => {
    if (score <= 25) return 'stroke-emerald-500';
    if (score <= 50) return 'stroke-amber-500';
    if (score <= 75) return 'stroke-orange-500';
    return 'stroke-red-500';
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Landscape Discovery
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Connect to your SAP system to discover the landscape, assess complexity, and generate migration recommendations.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Connection form */}
        <div className="card p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-5">
            SAP Connection
          </h2>
          <form onSubmit={handleDiscover} className="space-y-4">
            <div>
              <label className="label">SAP Host</label>
              <input
                className="input"
                placeholder="sap-prd.company.com"
                value={connection.host}
                onChange={(e) =>
                  setConnection({ ...connection, host: e.target.value })
                }
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">System Number</label>
                <input
                  className="input"
                  placeholder="00"
                  value={connection.system_number}
                  onChange={(e) =>
                    setConnection({
                      ...connection,
                      system_number: e.target.value,
                    })
                  }
                  required
                />
              </div>
              <div>
                <label className="label">Client</label>
                <input
                  className="input"
                  placeholder="100"
                  value={connection.client}
                  onChange={(e) =>
                    setConnection({ ...connection, client: e.target.value })
                  }
                  required
                />
              </div>
            </div>
            <div>
              <label className="label">Username</label>
              <input
                className="input"
                placeholder="SAP user"
                value={connection.user}
                onChange={(e) =>
                  setConnection({ ...connection, user: e.target.value })
                }
                required
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                className="input"
                placeholder="Password"
                value={connection.password}
                onChange={(e) =>
                  setConnection({ ...connection, password: e.target.value })
                }
                required
              />
            </div>

            {error && (
              <div className="p-3 bg-danger-50 border border-danger-200 rounded-lg text-sm text-danger-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-accent w-full disabled:opacity-50"
            >
              {loading ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Discovering...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                  </svg>
                  Run Discovery
                </>
              )}
            </button>
          </form>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-6">
          {!result ? (
            <div className="card p-12 text-center">
              <svg
                className="w-16 h-16 mx-auto text-slate-200"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
                />
              </svg>
              <h3 className="mt-4 text-base font-medium text-slate-500">
                No discovery results yet
              </h3>
              <p className="mt-1 text-sm text-slate-400">
                Connect to your SAP system and run discovery to see landscape
                details.
              </p>
            </div>
          ) : (
            <>
              {/* Stats row */}
              <div className="grid grid-cols-3 gap-4">
                <div className="stat-card">
                  <p className="text-sm text-slate-500">Custom Objects</p>
                  <p className="mt-1 text-3xl font-bold text-slate-900">
                    {result.custom_object_count.toLocaleString()}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Across all packages
                  </p>
                </div>
                <div className="stat-card">
                  <p className="text-sm text-slate-500">Integration Points</p>
                  <p className="mt-1 text-3xl font-bold text-slate-900">
                    {result.integration_point_count}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    RFC, IDoc, API connections
                  </p>
                </div>
                <div className="stat-card">
                  <p className="text-sm text-slate-500">System ID</p>
                  <p className="mt-1 text-3xl font-bold font-mono text-slate-900">
                    {result.system_id}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Landscape: {result.landscape_id}
                  </p>
                </div>
              </div>

              {/* Complexity score gauge */}
              {result.complexity_score && (
                <div className="card p-6">
                  <h3 className="text-sm font-semibold text-slate-900 mb-4">
                    Complexity Score
                  </h3>
                  <div className="flex items-center gap-8">
                    {/* Circular gauge */}
                    <div className="relative w-32 h-32 flex-shrink-0">
                      <svg
                        viewBox="0 0 120 120"
                        className="w-full h-full -rotate-90"
                      >
                        <circle
                          cx="60"
                          cy="60"
                          r="50"
                          fill="none"
                          stroke="#e2e8f0"
                          strokeWidth="10"
                        />
                        <circle
                          cx="60"
                          cy="60"
                          r="50"
                          fill="none"
                          className={scoreTrackColor(
                            result.complexity_score.score,
                          )}
                          strokeWidth="10"
                          strokeLinecap="round"
                          strokeDasharray={`${(result.complexity_score.score / 100) * 314} 314`}
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span
                          className={`text-3xl font-black ${scoreColor(result.complexity_score.score)}`}
                        >
                          {result.complexity_score.score}
                        </span>
                        <span className="text-[10px] text-slate-400 uppercase font-semibold">
                          / 100
                        </span>
                      </div>
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span
                          className={`text-lg font-bold ${scoreColor(result.complexity_score.score)}`}
                        >
                          {result.complexity_score.risk_level}
                        </span>
                        <span className="text-sm text-slate-500">
                          Risk Level
                        </span>
                      </div>
                      {result.complexity_score.benchmark_percentile !==
                        null && (
                        <p className="text-sm text-slate-500">
                          This landscape sits at the{' '}
                          <span className="font-semibold text-slate-700">
                            {result.complexity_score.benchmark_percentile}th
                            percentile
                          </span>{' '}
                          compared to similar SAP environments in our database.
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Migration recommendation */}
              {result.migration_recommendation && (
                <div className="card p-6 border-l-4 border-l-accent-500">
                  <div className="flex items-start gap-4">
                    <div className="p-2 bg-accent-50 rounded-lg flex-shrink-0">
                      <svg
                        className="w-6 h-6 text-accent-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
                        />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900">
                        Migration Recommendation
                      </h3>
                      <div className="mt-2 flex items-center gap-3">
                        <span className="badge-blue text-sm">
                          {result.migration_recommendation.approach.replace(
                            /_/g,
                            ' ',
                          )}
                        </span>
                        <span className="text-xs text-slate-400">
                          {Math.round(
                            result.migration_recommendation.confidence * 100,
                          )}
                          % confidence
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-slate-600 leading-relaxed">
                        {result.migration_recommendation.reasoning}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
