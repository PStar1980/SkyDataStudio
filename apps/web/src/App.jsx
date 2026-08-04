import { useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar.jsx';
import Topbar from './components/Topbar.jsx';
import StudioOverview from './pages/StudioOverview.jsx';
import PlaceholderPage from './pages/PlaceholderPage.jsx';

const PAGE_META = {
  '/dashboard': ['Studio Overview', 'Post-ingestion engineering command surface'],
  '/workspace/assets': ['Data Assets', 'Trusted source assets and downstream products'],
  '/workspace/pipelines': ['Pipelines', 'Versioned ETL and ELT processing definitions'],
  '/workspace/transformations': ['Transformations', 'SQL and Python transformation workbench'],
  '/workspace/models': ['Data Models', 'Staging, intermediate, mart, and semantic models'],
  '/orchestration/airflow': ['Apache Airflow', 'DAG, asset, scheduler, and executor observability'],
  '/orchestration/runs': ['Pipeline Runs', 'Durable batch execution evidence'],
  '/orchestration/backfills': ['Schedules & Backfills', 'Time, asset, and replay controls'],
  '/quality/checks': ['Data Quality', 'Tests, incidents, policies, and trust evidence'],
  '/quality/contracts': ['Contracts', 'Schema and consumer compatibility'],
  '/quality/lineage': ['Lineage', 'Upstream, downstream, and change impact'],
  '/delivery/marts': ['Analytical Marts', 'Curated consumer-ready facts and dimensions'],
  '/delivery/semantic': ['Semantic Layer', 'Governed metrics and business definitions'],
  '/delivery/reports': ['Reports', 'Reporting inventory and refresh evidence'],
  '/delivery/power-bi': ['Power BI', 'Semantic models, refreshes, and deployment'],
  '/configuration/connections': ['Connections', 'Read-only sources and governed targets'],
  '/configuration/environments': ['Environments', 'Development, test, and production profiles'],
  '/configuration/settings': ['Settings', 'Studio configuration and feature controls'],
};

function App() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pageTitle, pageSubtitle] = useMemo(
    () => PAGE_META[location.pathname] ?? ['SkyData Studio', 'Data Engineering Workbench'],
    [location.pathname],
  );

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [location.pathname]);

  return (
    <div className="studio-shell">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <Topbar
        pageTitle={pageTitle}
        pageSubtitle={pageSubtitle}
        onMenu={() => setMobileOpen(true)}
      />
      <main className="studio-main">
        <Routes>
          <Route path="/" element={<Navigate replace to="/dashboard" />} />
          <Route path="/dashboard" element={<StudioOverview />} />
          {Object.entries(PAGE_META)
            .filter(([path]) => path !== '/dashboard')
            .map(([path, [title, subtitle]]) => (
              <Route
                key={path}
                path={path}
                element={<PlaceholderPage title={title} subtitle={subtitle} />}
              />
            ))}
          <Route path="*" element={<Navigate replace to="/dashboard" />} />
        </Routes>
      </main>
      {mobileOpen ? <button className="sidebar-scrim" onClick={() => setMobileOpen(false)} /> : null}
    </div>
  );
}

export default App;
