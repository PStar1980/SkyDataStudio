import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY = {
  product_status: 'PENDING',
  product_code: 'FED_FUNDS_RATE_DAILY_PRODUCT',
  product_version: '1.0.0',
  product_name: 'Federal Funds Rate Daily Analytical Product',
  description: 'Waiting for analytical publication evidence.',
  owner: 'SkyData Studio',
  domain: 'Macroeconomics',
  source_path: 'contracts/analytics/products/fed_funds_rate_daily_product.v1.json',
  source_relation: { relation: 'mart.fed_funds_rate', status: 'MISSING', row_count: null, max_freshness_value: null },
  mart_relation: { relation: 'dbt_mart.fct_fed_funds_rate_daily', status: 'MISSING', row_count: null, max_freshness_value: null },
  row_count_delta: null,
  freshness_status: 'UNKNOWN',
  refresh_required: false,
  model_build_status: 'UNKNOWN',
  semantic_artifact_status: 'PENDING',
  semantic_model_resolved: false,
  quality_contract_status: 'PENDING',
  required_metric_count: 4,
  resolved_metric_count: 0,
  required_consumer_count: 1,
  resolved_consumer_count: 0,
  gates: [],
  publication_message: 'Waiting for analytical publication evidence.',
};

function formatCount(value) {
  if (value === null || value === undefined) return '—';
  return Number(value).toLocaleString();
}

function gateTone(status) {
  if (status === 'PASS') return 'READY';
  if (status === 'WARN' || status === 'PENDING') return 'WARNING';
  if (status === 'BLOCK') return 'BLOCKED';
  return 'UNKNOWN';
}

function statusTone(status) {
  if (status === 'READY' || status === 'ALIGNED' || status === 'COMPLIANT') return 'READY';
  if (status === 'STALE' || status === 'PENDING' || status === 'UNKNOWN') return 'WARNING';
  if (status === 'BLOCKED' || status === 'MISSING' || status === 'ERROR') return 'BLOCKED';
  return status;
}

function AnalyticalMarts() {
  const [summary, setSummary] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await getJson('/api/v1/analytics/products/summary'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/analytics/products/summary', { signal: controller.signal })
      .then(setSummary)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const passingGates = useMemo(
    () => summary.gates.filter((gate) => gate.status === 'PASS').length,
    [summary.gates],
  );

  return (
    <div className="page-stack analytical-marts-page">
      <section className="workspace-intro analytical-marts-intro">
        <div>
          <span className="eyebrow">PHASE 9.1 · ANALYTICAL MART PUBLICATION READINESS</span>
          <h1>Analytical Marts</h1>
          <p>
            Treat a mart as publishable only when physical data, dbt build evidence, freshness,
            quality policy, semantic definitions, and declared consumers all agree.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={load} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh Product'}
        </button>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <section className="metric-grid analytical-product-metrics">
        <article className="metric-card">
          <span>Publication Gate</span>
          <strong>{summary.product_status}</strong>
          <small>{passingGates}/{summary.gates.length || 6} gates passing</small>
        </article>
        <article className="metric-card">
          <span>Source Rows</span>
          <strong>{formatCount(summary.source_relation.row_count)}</strong>
          <small>{summary.source_relation.relation}</small>
        </article>
        <article className="metric-card">
          <span>Mart Rows</span>
          <strong>{formatCount(summary.mart_relation.row_count)}</strong>
          <small>{summary.mart_relation.relation}</small>
        </article>
        <article className="metric-card">
          <span>Freshness</span>
          <strong>{summary.freshness_status}</strong>
          <small>{summary.row_count_delta === null ? 'Row delta pending' : `${summary.row_count_delta} row delta`}</small>
        </article>
        <article className="metric-card">
          <span>Metrics</span>
          <strong>{summary.resolved_metric_count}/{summary.required_metric_count}</strong>
          <small>Governed semantic measures</small>
        </article>
        <article className="metric-card">
          <span>Consumers</span>
          <strong>{summary.resolved_consumer_count}/{summary.required_consumer_count}</strong>
          <small>Declared delivery contracts</small>
        </article>
      </section>

      <section className={`panel analytical-product-hero status-${String(summary.product_status).toLowerCase()}`}>
        <div className="panel-heading">
          <div>
            <span className="eyebrow">ANALYTICAL PRODUCT</span>
            <h2>{summary.product_name}</h2>
          </div>
          <StatusPill status={statusTone(summary.product_status)} />
        </div>
        <p className="analytical-product-message">{summary.publication_message}</p>
        {summary.refresh_required ? (
          <div className="analytical-refresh-callout">
            <strong>Fresh dbt materialization required</strong>
            <span>Run <code>.\scripts\dbt.ps1 build</code>, then refresh this page.</span>
          </div>
        ) : null}
        <div className="analytical-product-contract-grid">
          <div><span>PRODUCT</span><strong>{summary.product_code}</strong><small>v{summary.product_version}</small></div>
          <div><span>DOMAIN</span><strong>{summary.domain}</strong><small>{summary.owner}</small></div>
          <div><span>DBT BUILD</span><strong>{summary.model_build_status}</strong><small>Latest mart artifact state</small></div>
          <div><span>QUALITY</span><strong>{summary.quality_contract_status}</strong><small>Source-controlled publication policy</small></div>
          <div><span>SEMANTIC</span><strong>{summary.semantic_model_resolved ? 'RESOLVED' : 'PENDING'}</strong><small>{summary.semantic_artifact_status} artifacts</small></div>
          <div><span>CONTRACT</span><strong>GATED</strong><small>{summary.source_path}</small></div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">FRESHNESS EVIDENCE</span>
            <h2>Curated source and analytical mart must move together</h2>
          </div>
          <StatusPill status={statusTone(summary.freshness_status)} />
        </div>
        <div className="analytical-relation-grid">
          <article>
            <span>CURATED SOURCE</span>
            <h3>{summary.source_relation.relation}</h3>
            <strong>{formatCount(summary.source_relation.row_count)} rows</strong>
            <small>Latest {summary.source_relation.max_freshness_value || '—'}</small>
          </article>
          <div className="analytical-freshness-arrow">
            <span>→</span>
            <strong>{summary.freshness_status}</strong>
            <small>{summary.row_count_delta === null ? 'delta pending' : `${summary.row_count_delta} rows`}</small>
          </div>
          <article>
            <span>DBT MART</span>
            <h3>{summary.mart_relation.relation}</h3>
            <strong>{formatCount(summary.mart_relation.row_count)} rows</strong>
            <small>Latest {summary.mart_relation.max_freshness_value || '—'}</small>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">PUBLICATION GATES</span>
            <h2>Six independent proofs decide whether delivery is safe</h2>
          </div>
          <span className="panel-count">{passingGates}/{summary.gates.length || 6} pass</span>
        </div>
        <div className="analytical-gate-grid">
          {summary.gates.map((gate, index) => (
            <article className="analytical-gate-card" key={gate.code}>
              <div>
                <span>0{index + 1} · {gate.code.replaceAll('_', ' ')}</span>
                <StatusPill status={gateTone(gate.status)} />
              </div>
              <h3>{gate.label}</h3>
              <p>{gate.message}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="two-column-grid analytical-proof-grid">
        <article className="panel compact-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">ACCEPTANCE CONTRACT</span><h2>What Phase 9.1 proves</h2></div>
            <span className="phase-badge">9.1</span>
          </div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Freshness is a gate</strong><small>A healthy dbt model is not publishable when the curated source has moved ahead.</small></div></li>
            <li><span>02</span><div><strong>Governance composes</strong><small>Physical, quality, semantic, and consumer evidence must all resolve together.</small></div></li>
            <li><span>03</span><div><strong>Publication stays explicit</strong><small>Studio reports readiness but does not silently execute dbt or deploy Power BI resources.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">BOUNDARY</span><h2>Gate the product; do not hide the refresh</h2></div>
            <span className="rule-mark">▦</span>
          </div>
          <p className="rule-copy">
            Phase 9.1 turns the existing mart into a governed analytical product contract. dbt still
            owns transformation execution, quality retains policy ownership, semantic definitions
            remain dbt-owned, and downstream Power BI provisioning stays a later phase.
          </p>
          <div className="rule-footer"><span>Freshness proof</span><span>Governed delivery</span><span>No hidden execution</span></div>
        </article>
      </section>
    </div>
  );
}

export default AnalyticalMarts;
