import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Programme } from '../types';

export default function HanaBigQueryLanding() {
  const navigate = useNavigate();
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.listProgrammes();
      setProgrammes(res.programmes);
    } catch {
      setProgrammes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">HANA → BigQuery</h1>
        <p className="mt-1 text-sm text-slate-500">
          Replicate SAP HANA tables into Google BigQuery. Select a programme to
          define pipelines, validate connectivity, and run extract → stage → load jobs.
        </p>
      </div>

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
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
            </svg>
            <h3 className="mt-4 text-sm font-medium text-slate-900">No programmes yet</h3>
            <p className="mt-1 text-sm text-slate-500">
              Create a programme first, then come back to set up HANA → BigQuery pipelines.
            </p>
            <button onClick={() => navigate('/programmes')} className="btn-primary mt-4">
              Go to Programmes
            </button>
          </div>
        ) : (
          <div>
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
              <h2 className="text-sm font-semibold text-slate-700">Select a programme</h2>
            </div>
            <div className="divide-y divide-slate-100">
              {programmes.map((p) => (
                <button
                  key={p.id}
                  onClick={() => navigate(`/hana-bigquery/${p.id}`)}
                  className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50 transition-colors text-left"
                >
                  <div>
                    <span className="text-sm font-semibold text-slate-900">{p.name}</span>
                    <span className="ml-3 text-xs font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                      {p.customer_id}
                    </span>
                  </div>
                  <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
