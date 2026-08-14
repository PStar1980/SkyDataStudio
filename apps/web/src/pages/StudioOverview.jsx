import { useEffect, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';

const FALLBACK = {
  product: 'SkyData Studio',
  subtitle: 'Data Engineering Workbench',
  theme: 'Aurora Foundry',
  current_phase: 'Phase 9.1 — Analytical Mart Publication Readiness and Freshness Gate',
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
          <span className="eyebrow">AURORA FOUNDRY · PHASE 9.1</span>
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
        <article className="metric-card"><span>Current Phase</span><strong>9.1</strong><small>analytical mart publication readiness</small></article>
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
            { code: 'DBT', name: 'dbt Transformation Layer', description: 'Tested staging, intermediate, mart, and semantic models.', status: 'FOUNDATION', phase: 6 },
            { code: 'QUALITY_LINEAGE', name: 'Data Quality and Reliability', description: 'Trust evidence, contracts, incidents, and reliability history.', status: 'READY', phase: 7 },
            { code: 'LINEAGE_IMPACT', name: 'Lineage and Impact Analysis', description: 'Federated asset, field, trust, runtime, and consumer impact analysis.', status: 'READY', phase: 8 },
            { code: 'ANALYTICS_DELIVERY', name: 'Analytics Delivery', description: 'Governed analytical marts and publication readiness for downstream consumers.', status: 'FOUNDATION', phase: 9 },
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
          <div className="panel-heading"><div><span className="eyebrow">CURRENT IMPLEMENTATION</span><h2>analytical mart publication readiness</h2></div><span className="phase-badge">PHASE 9.1</span></div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Freshness becomes explicit</strong><small>Curated-source and dbt-mart row/date evidence must align before publication is ready.</small></div></li>
            <li><span>02</span><div><strong>Governance composes</strong><small>Quality, semantic metrics, and declared consumers join the physical mart proof.</small></div></li>
            <li><span>03</span><div><strong>Delivery remains gated</strong><small>Studio reports publication readiness without silently executing dbt or fabricating Power BI deployment.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">ENGINEERING RULE</span><h2>Contracts before coupling</h2></div><span className="rule-mark">∞</span></div>
          <p className="rule-copy">Studio composes evidence from physical relations, dbt artifacts, quality policy, semantic definitions, and consumer declarations while each authority remains independently owned.</p>
          <div className="rule-footer"><span>Freshness proof</span><span>Governed delivery</span><span>Auditable evidence</span></div>
        </article>
      </section>
    </div>
  );
}

export default StudioOverview;
