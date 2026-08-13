import { useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar.jsx';
import Topbar from './components/Topbar.jsx';
import StudioOverview from './pages/StudioOverview.jsx';
import DataAssets from './pages/DataAssets.jsx';
import MetadataRegistry from './pages/MetadataRegistry.jsx';
import SourceMappings from './pages/SourceMappings.jsx';
import Pipelines from './pages/Pipelines.jsx';
import PipelineRuns from './pages/PipelineRuns.jsx';
import Airflow from './pages/Airflow.jsx';
import SchedulesBackfills from './pages/SchedulesBackfills.jsx';
import Transformations from './pages/Transformations.jsx';
import DataModels from './pages/DataModels.jsx';
import SemanticLayer from './pages/SemanticLayer.jsx';
import DataQuality from './pages/DataQuality.jsx';
import DataContracts from './pages/DataContracts.jsx';
import QualityIncidents from './pages/QualityIncidents.jsx';
import QualityReliability from './pages/QualityReliability.jsx';
import Lineage from './pages/Lineage.jsx';
import PlaceholderPage from './pages/PlaceholderPage.jsx';

const PAGE_META = {
  '/dashboard': ['Studio Overview', 'Post-ingestion engineering command surface'],
  '/workspace/assets': ['Data Assets', 'Trusted source assets and downstream products'],
  '/workspace/registry': ['Metadata Registry', 'Studio-owned engineering metadata and data products'],
  '/workspace/mappings': ['Source Mappings', 'Source-to-target specifications, field transformations, and lineage'],
  '/workspace/pipelines': ['Pipelines', 'Versioned ETL and ELT processing definitions'],
  '/workspace/transformations': ['Transformations', 'SQL and Python transformation workbench'],
  '/workspace/models': ['Data Models', 'Staging, intermediate, mart, and semantic models'],
  '/orchestration/airflow': ['Apache Airflow', 'DAG, asset, scheduler, and executor observability'],
  '/orchestration/runs': ['Pipeline Runs', 'Durable batch execution evidence'],
  '/orchestration/backfills': ['Schedules & Backfills', 'Time, asset, and replay controls'],
  '/quality/checks': ['Data Quality', 'Tests, coverage, and trust evidence'],
  '/quality/contracts': ['Contracts', 'Quality gates and consumer compatibility'],
  '/quality/incidents': ['Quality Incidents', 'Durable failures, ownership, and remediation history'],
  '/quality/reliability': ['Reliability', 'Quality SLO, observation history, and consumer-readiness posture'],
  '/quality/lineage': ['Lineage', 'Asset, field, trust, runtime, and consumer impact'],
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
          <Route path="/workspace/assets" element={<DataAssets />} />
          <Route path="/workspace/registry" element={<MetadataRegistry />} />
          <Route path="/workspace/mappings" element={<SourceMappings />} />
          <Route path="/workspace/pipelines" element={<Pipelines />} />
          <Route path="/workspace/transformations" element={<Transformations />} />
          <Route path="/workspace/models" element={<DataModels />} />
          <Route path="/delivery/semantic" element={<SemanticLayer />} />
          <Route path="/quality/checks" element={<DataQuality />} />
          <Route path="/quality/contracts" element={<DataContracts />} />
          <Route path="/quality/incidents" element={<QualityIncidents />} />
          <Route path="/quality/reliability" element={<QualityReliability />} />
          <Route path="/quality/lineage" element={<Lineage />} />
          <Route path="/orchestration/airflow" element={<Airflow />} />
          <Route path="/orchestration/runs" element={<PipelineRuns />} />
          <Route path="/orchestration/backfills" element={<SchedulesBackfills />} />
          {Object.entries(PAGE_META)
            .filter(([path]) => ![
              '/dashboard',
              '/workspace/assets',
              '/workspace/registry',
              '/workspace/mappings',
              '/workspace/pipelines',
              '/workspace/transformations',
              '/workspace/models',
              '/orchestration/airflow',
              '/orchestration/runs',
              '/orchestration/backfills',
              '/delivery/semantic',
              '/quality/checks',
              '/quality/contracts',
              '/quality/incidents',
              '/quality/reliability',
              '/quality/lineage',
            ].includes(path))
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
