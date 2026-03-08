import { useNavigate } from 'react-router-dom';

const stats = [
  {
    label: 'Active Programmes',
    value: '3',
    change: '+1 this month',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
      </svg>
    ),
    color: 'text-primary-600 bg-primary-50',
  },
  {
    label: 'Objects Analysed',
    value: '12,847',
    change: '2,340 this week',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
      </svg>
    ),
    color: 'text-accent-600 bg-accent-50',
  },
  {
    label: 'Remediations Generated',
    value: '1,923',
    change: '89% auto-resolved',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l-5.36 3.15 1.03-5.97L2.76 8.17l6.01-.87L11.42 2l2.65 5.3 6.01.87-4.33 4.18 1.03 5.97z" />
      </svg>
    ),
    color: 'text-violet-600 bg-violet-50',
  },
  {
    label: 'Assessment Reports',
    value: '7',
    change: '2 pending review',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
    color: 'text-amber-600 bg-amber-50',
  },
];

const moduleStatus = [
  { id: 'M01', name: 'Discovery Engine', status: 'active', description: 'SAP landscape discovery and complexity assessment' },
  { id: 'M02', name: 'ABAP Intelligence', status: 'active', description: 'AI-powered code analysis and compatibility scanning' },
  { id: 'M03', name: 'Remediation Studio', status: 'planned', description: 'Automated code fix generation with human review' },
  { id: 'M04', name: 'Data Readiness', status: 'planned', description: 'Data migration profiling and validation' },
  { id: 'M05', name: 'Test Engine', status: 'planned', description: 'Automated regression test generation' },
  { id: 'M06', name: 'Migration Execution', status: 'planned', description: 'Orchestrated cutover and go-live management' },
  { id: 'M07', name: 'Observability', status: 'planned', description: 'Real-time monitoring and anomaly detection' },
];

const recentActivity = [
  { action: 'Analysis completed', target: 'Acme Corp ECC 6.0', time: '2 hours ago', type: 'success' },
  { action: 'Discovery started', target: 'Global Industries S/4', time: '5 hours ago', type: 'info' },
  { action: 'Remediation generated', target: 'ZFI_PAYMENT_PROC', time: '1 day ago', type: 'success' },
  { action: 'Programme created', target: 'TechCo Migration 2026', time: '2 days ago', type: 'info' },
  { action: 'Report exported', target: 'Q3 Assessment Report', time: '3 days ago', type: 'neutral' },
];

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          HanaForge Command Centre
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          AI-native SAP S/4HANA migration platform -- overview and quick actions
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((stat) => (
          <div key={stat.label} className="stat-card">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500">
                  {stat.label}
                </p>
                <p className="mt-2 text-3xl font-bold text-slate-900">
                  {stat.value}
                </p>
                <p className="mt-1 text-xs text-slate-400">{stat.change}</p>
              </div>
              <div className={`p-2.5 rounded-lg ${stat.color}`}>
                {stat.icon}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick actions + recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick actions */}
        <div className="card p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-4">
            Quick Actions
          </h2>
          <div className="space-y-3">
            <button
              onClick={() => navigate('/programmes')}
              className="btn-primary w-full"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              New Programme
            </button>
            <button
              onClick={() => navigate('/programmes')}
              className="btn-secondary w-full"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
              Upload ABAP Source
            </button>
            <button className="btn-secondary w-full opacity-60 cursor-not-allowed" disabled>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              Generate Report
            </button>
          </div>
        </div>

        {/* Recent activity */}
        <div className="card p-6 lg:col-span-2">
          <h2 className="text-base font-semibold text-slate-900 mb-4">
            Recent Activity
          </h2>
          <div className="space-y-0">
            {recentActivity.map((item, i) => (
              <div
                key={i}
                className={`flex items-center gap-4 py-3 ${
                  i > 0 ? 'border-t border-slate-100' : ''
                }`}
              >
                <div
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    item.type === 'success'
                      ? 'bg-emerald-500'
                      : item.type === 'info'
                        ? 'bg-blue-500'
                        : 'bg-slate-300'
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-700">
                    <span className="font-medium">{item.action}</span>
                    <span className="text-slate-400"> -- </span>
                    <span className="text-slate-500">{item.target}</span>
                  </p>
                </div>
                <span className="text-xs text-slate-400 flex-shrink-0">
                  {item.time}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Module status grid */}
      <div>
        <h2 className="text-base font-semibold text-slate-900 mb-4">
          Module Status
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {moduleStatus.map((mod) => (
            <div key={mod.id} className="card-hover p-5">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-xs font-mono font-bold text-slate-400">
                  {mod.id}
                </span>
                <span
                  className={
                    mod.status === 'active' ? 'badge-green' : 'badge-slate'
                  }
                >
                  {mod.status === 'active' ? 'Active' : 'Planned'}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-slate-800">
                {mod.name}
              </h3>
              <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                {mod.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
