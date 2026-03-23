import { NavLink, Outlet, useLocation } from 'react-router-dom';

const modules = [
  { id: 'M01', name: 'Discovery', color: 'bg-emerald-400', ready: true },
  { id: 'M02', name: 'ABAP Intelligence', color: 'bg-blue-400', ready: true },
  { id: 'M03', name: 'Data Readiness', color: 'bg-violet-400', ready: true },
  { id: 'M08', name: 'HANA → BigQuery', color: 'bg-indigo-400', ready: true },
  { id: 'M04', name: 'TestForge', color: 'bg-amber-400', ready: true },
  { id: 'M05', name: 'Infrastructure', color: 'bg-rose-400', ready: true },
  { id: 'M06', name: 'Migration Exec', color: 'bg-cyan-400', ready: true },
  { id: 'M07', name: 'Cutover', color: 'bg-slate-400', ready: true },
];

function buildBreadcrumbs(pathname: string): { label: string; href: string }[] {
  const crumbs: { label: string; href: string }[] = [
    { label: 'HanaForge', href: '/' },
  ];

  const segments = pathname.split('/').filter(Boolean);

  if (segments[0] === 'programmes') {
    crumbs.push({ label: 'Programmes', href: '/programmes' });
    if (segments[1]) {
      crumbs.push({
        label: 'Programme Detail',
        href: `/programmes/${segments[1]}`,
      });
      if (segments[2] === 'discovery') {
        crumbs.push({
          label: 'Discovery',
          href: `/programmes/${segments[1]}/discovery`,
        });
      }
      if (segments[2] === 'analysis') {
        crumbs.push({
          label: 'ABAP Analysis',
          href: `/programmes/${segments[1]}/analysis`,
        });
      }
      if (segments[2] === 'data-readiness') {
        crumbs.push({
          label: 'Data Readiness',
          href: `/programmes/${segments[1]}/data-readiness`,
        });
      }
      if (segments[2] === 'hana-bigquery') {
        crumbs.push({
          label: 'HANA → BigQuery',
          href: `/programmes/${segments[1]}/hana-bigquery`,
        });
      }
      if (segments[2] === 'test-forge') {
        crumbs.push({
          label: 'TestForge',
          href: `/programmes/${segments[1]}/test-forge`,
        });
      }
      if (segments[2] === 'infrastructure') {
        crumbs.push({
          label: 'Infrastructure',
          href: `/programmes/${segments[1]}/infrastructure`,
        });
      }
      if (segments[2] === 'migration') {
        crumbs.push({
          label: 'Migration',
          href: `/programmes/${segments[1]}/migration`,
        });
      }
      if (segments[2] === 'cutover') {
        crumbs.push({
          label: 'Cutover',
          href: `/programmes/${segments[1]}/cutover`,
        });
      }
    }
  }

  return crumbs;
}

export default function Layout() {
  const location = useLocation();
  const breadcrumbs = buildBreadcrumbs(location.pathname);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-slate-900 flex flex-col">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-800">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center shadow-lg shadow-accent-900/30">
            <svg
              className="w-5 h-5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-white text-lg font-bold tracking-tight">
              HanaForge
            </h1>
            <p className="text-slate-500 text-[10px] font-medium uppercase tracking-widest">
              Migration Platform
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <p className="px-4 pb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
            Navigation
          </p>
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
            </svg>
            Dashboard
          </NavLink>
          <NavLink
            to="/programmes"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
            </svg>
            Programmes
          </NavLink>

          {/* Module indicators */}
          <div className="pt-6">
            <p className="px-4 pb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
              Modules
            </p>
            <div className="space-y-0.5">
              {modules.map((mod) => (
                <div
                  key={mod.id}
                  className="flex items-center gap-3 px-4 py-2 rounded-lg text-sm"
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      mod.ready ? mod.color : 'bg-slate-600'
                    }`}
                  />
                  <span
                    className={`font-mono text-[10px] ${
                      mod.ready ? 'text-slate-400' : 'text-slate-600'
                    }`}
                  >
                    {mod.id}
                  </span>
                  <span
                    className={`text-sm ${
                      mod.ready
                        ? 'text-slate-300 font-medium'
                        : 'text-slate-600'
                    }`}
                  >
                    {mod.name}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </nav>

        {/* Sidebar footer */}
        <div className="px-4 py-4 border-t border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
              <span className="text-white text-xs font-bold">HF</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-300 font-medium truncate">
                HanaForge v1.0
              </p>
              <p className="text-xs text-slate-500 truncate">
                Enterprise Edition
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-8 py-4 bg-white border-b border-slate-200">
          <nav className="flex items-center gap-1.5 text-sm">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.href} className="flex items-center gap-1.5">
                {i > 0 && (
                  <svg
                    className="w-4 h-4 text-slate-300"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M8.25 4.5l7.5 7.5-7.5 7.5"
                    />
                  </svg>
                )}
                <span
                  className={
                    i === breadcrumbs.length - 1
                      ? 'text-slate-800 font-semibold'
                      : 'text-slate-400 hover:text-slate-600 transition-colors'
                  }
                >
                  {crumb.label}
                </span>
              </span>
            ))}
          </nav>
          <div className="flex items-center gap-4">
            <button className="relative p-2 text-slate-400 hover:text-slate-600 transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
              </svg>
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent-500 rounded-full" />
            </button>
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center cursor-pointer shadow-sm">
              <span className="text-white text-sm font-bold">U</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
