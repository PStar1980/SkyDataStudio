import { useEffect, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';

const FALLBACK = {
  product: 'SkyData Studio',
  subtitle: 'Data Engineering Workbench',
  theme: 'Aurora Foundry',
  current_phase: 'Phase 5.3 — Airflow Schedules and Controlled Backfills',
  boundary: 'SkyData Studio starts after SkyCommand ingestion and publishes governed analytical products for downstream consumers.',
  capabilities: [],
};

const FLOW = [
  ['SkyCommand', 'Trusted ingestion + catalogue', 'command'],
  ['SkyData Studio', 'Transform + model + govern', 'studio'],
  ['SkyWeb / Power BI', 'Explore + communicate', 'delivery'],
];

function StudioOverview() {
  const [summary, setSummary] = useState(FALLBACK);
  const [apiState, setApiState] = useState('CONNECTING');

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/v1/platform/summary', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`API returned ${response.status}`);
        return response.json();
      })
      .then((data) => {
        setSummary(data);
        setApiState('CONNECTED');
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setApiState('OFFLINE PREVIEW');
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <span className="eyebrow">AURORA FOUNDRY · PHASE 5.3</span>
          <h1>Shape trusted data into analytical products.</h1>
          <p>{summary.boundary}</p>
          <div className="hero-actions">
            <button className="primary-button" type="button">Open Roadmap</button>
            <button className="secondary-button" type="button">Inspect Contracts</button>
          </div>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <div className="orbit-ring ring-one" />
          <div className="orbit-ring ring-two" />
          <div className="orbit-core">SDS</div>
          <span className="orbit-node node-one">SQL</span>
          <span className="orbit-node node-two">dbt</span>
          <span className="orbit-node node-three">DAG</span>
        </div>
      </section>

      <section className="metric-grid">
        <article className="metric-card"><span>Platform API</span><strong>{apiState}</strong><small>FastAPI contract service</small></article>
        <article className="metric-card"><span>Current Phase</span><strong>5.3</strong><small>Schedules + controlled backfills</small></article>
        <article className="metric-card"><span>Pipeline Proof</span><strong>READY</strong><small>Curated mart materialization proven</small></article>
        <article className="metric-card"><span>Orchestrator</span><strong>Airflow 3</strong><small>Batch and asset workflows</small></article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">PRODUCT BOUNDARIES</span><h2>One data journey, three focused systems</h2></div>
          <StatusPill status="FOUNDATION" />
        </div>
        <div className="flow-grid">
          {FLOW.map(([name, detail, kind], index) => (
            <div className={`flow-node flow-${kind}`} key={name}>
              <span className="flow-index">0{index + 1}</span>
              <strong>{name}</strong>
              <small>{detail}</small>
              {index < FLOW.length - 1 ? <span className="flow-arrow">→</span> : null}
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">CAPABILITY MAP</span><h2>Data engineering platform trajectory</h2></div>
          <span className="panel-meta">{summary.theme}</span>
        </div>
        <div className="capability-grid">
          {(summary.capabilities.length ? summary.capabilities : [
            { code: 'CONTRACT_BRIDGE', name: 'SkyCommand Contract Bridge', description: 'Typed read-only integration with trusted ingestion contracts.', status: 'FOUNDATION', phase: 2 },
            { code: 'METADATA_REGISTRY', name: 'Metadata Registry + Blueprints', description: 'Studio-owned assets, target schemas, ownership, source-to-target mappings, and lineage.', status: 'FOUNDATION', phase: 3 },
            { code: 'PIPELINE_WORKBENCH', name: 'ETL/ELT Pipeline Workbench', description: 'Versioned post-ingestion pipelines and structured run evidence.', status: 'READY', phase: 4 },
            { code: 'AIRFLOW', name: 'Apache Airflow Orchestration', description: 'DAGs, assets, schedules, retries, and backfills.', status: 'FOUNDATION', phase: 5 },
            { code: 'DBT', name: 'dbt Transformation Layer', description: 'Tested staging, intermediate, mart, and semantic models.', status: 'SCAFFOLDED', phase: 6 },
            { code: 'QUALITY_LINEAGE', name: 'Quality and Lineage', description: 'Trust evidence, dependencies, incidents, and impact analysis.', status: 'PLANNED', phase: 7 },
            { code: 'ANALYTICS_DELIVERY', name: 'Analytics Delivery', description: 'Governed products for SkyWeb Analytics and Power BI.', status: 'PLANNED', phase: 9 },
          ]).map((capability) => (
            <article className="capability-card" key={capability.code}>
              <div className="capability-top"><span>Phase {capability.phase}</span><StatusPill status={capability.status} /></div>
              <h3>{capability.name}</h3>
              <p>{capability.description}</p>
              <div className="capability-track"><span style={{ width: capability.status === 'READY' ? '100%' : capability.status === 'FOUNDATION' ? '28%' : capability.status === 'SCAFFOLDED' ? '14%' : '4%' }} /></div>
            </article>
          ))}
        </div>
      </section>

      <section className="two-column-grid">
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">CURRENT IMPLEMENTATION</span><h2>Airflow scheduling + backfill controls</h2></div><span className="phase-badge">PHASE 5.3</span></div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Daily Airflow timetable</strong><small>Run the DFF DAG on a time-based schedule while preserving the same Studio execution contract.</small></div></li>
            <li><span>02</span><div><strong>Controlled backfill API</strong><small>Create bounded replay windows through Airflow REST API v2 without metadata-database reads.</small></div></li>
            <li><span>03</span><div><strong>Replay-safe interval dates</strong><small>Scheduled and backfill runs derive RUN_DATE from the Airflow data interval.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">ENGINEERING RULE</span><h2>Contracts before coupling</h2></div><span className="rule-mark">∞</span></div>
          <p className="rule-copy">Studio consumes versioned APIs and approved read-only views. It does not write into SkyCommand schemas or read Airflow's internal metadata database.</p>
          <div className="rule-footer"><span>Reusable architecture</span><span>Portable domains</span><span>Auditable evidence</span></div>
        </article>
      </section>
    </div>
  );
}

export default StudioOverview;
