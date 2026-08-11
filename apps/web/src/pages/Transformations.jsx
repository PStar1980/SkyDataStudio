import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY_SUMMARY = {
  runtime: 'DOCKER',
  adapter: 'POSTGRES',
  dbt_core_version: '1.12.0',
  dbt_postgres_version: '1.11.0',
  source_relation: 'mart.fed_funds_rate',
  model_count: 3,
  ready_model_count: 0,
  test_count: 14,
  layers_ready: 0,
  layer_count: 3,
  relations: [],
};

function formatNumber(value) {
  return typeof value === 'number' ? value.toLocaleString() : '—';
}

function Transformations() {
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await getJson('/api/v1/transformations/dbt/summary'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    getJson('/api/v1/transformations/dbt/summary', { signal: controller.signal })
      .then(setSummary)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, []);

  const modelRelations = useMemo(
    () => summary.relations.filter((relation) => relation.layer !== 'SOURCE'),
    [summary.relations],
  );
  const sourceRelation = summary.relations.find((relation) => relation.layer === 'SOURCE');
  const allModelsReady = summary.ready_model_count === summary.model_count;

  return (
    <div className="page-stack transformation-page">
      <section className="workspace-intro transformation-intro">
        <div>
          <span className="eyebrow">PHASE 6.1 · DBT RUNTIME + LAYERED MODEL FOUNDATION</span>
          <h1>Transformations</h1>
          <p>
            Build tested SQL models over Studio-owned curated data while keeping the dbt runtime
            isolated, repeatable, and explicitly separated into staging, intermediate, and mart layers.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={loadSummary} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh Models'}
        </button>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <section className="metric-grid transformation-metric-grid">
        <article className="metric-card">
          <span>Runtime</span>
          <strong>{summary.runtime}</strong>
          <small>Ephemeral Docker execution</small>
        </article>
        <article className="metric-card">
          <span>Adapter</span>
          <strong>{summary.adapter}</strong>
          <small>dbt-postgres {summary.dbt_postgres_version}</small>
        </article>
        <article className="metric-card">
          <span>Models</span>
          <strong>{summary.ready_model_count}/{summary.model_count}</strong>
          <small>{allModelsReady ? 'All layered relations materialized' : 'Awaiting first dbt build'}</small>
        </article>
        <article className="metric-card">
          <span>Data Tests</span>
          <strong>{summary.test_count}</strong>
          <small>Source + model quality assertions</small>
        </article>
        <article className="metric-card">
          <span>Layers</span>
          <strong>{summary.layers_ready}/{summary.layer_count}</strong>
          <small>Staging → intermediate → mart</small>
        </article>
      </section>

      <section className="panel transformation-source-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">SOURCE CONTRACT</span>
            <h2>Phase 4.3 curated data becomes the dbt source seam</h2>
          </div>
          <StatusPill status={sourceRelation?.status ?? 'MISSING'} />
        </div>
        <div className="transformation-source-grid">
          <article>
            <span>RELATION</span>
            <strong>{summary.source_relation}</strong>
            <small>Studio-owned replay-safe materialization</small>
          </article>
          <article>
            <span>ROWS</span>
            <strong>{formatNumber(sourceRelation?.row_count)}</strong>
            <small>Expected proof baseline: 26,335</small>
          </article>
          <article>
            <span>DBT CORE</span>
            <strong>{summary.dbt_core_version}</strong>
            <small>Container-pinned runtime</small>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">LAYERED MODEL GRAPH</span>
            <h2>One source, three explicit transformation boundaries</h2>
          </div>
          <StatusPill status={allModelsReady ? 'READY' : 'FOUNDATION'} />
        </div>
        <div className="transformation-flow-grid">
          {modelRelations.length ? modelRelations.map((relation, index) => (
            <article className="transformation-model-card" key={relation.relation}>
              <div>
                <span>0{index + 1} · {relation.layer}</span>
                <StatusPill status={relation.status} />
              </div>
              <strong>{relation.name}</strong>
              <code>{relation.relation}</code>
              <p>{relation.description}</p>
              <footer>
                <span>{relation.materialization}</span>
                <span>{formatNumber(relation.row_count)} rows</span>
              </footer>
              {index < modelRelations.length - 1 ? <b aria-hidden="true">→</b> : null}
            </article>
          )) : ['STAGING', 'INTERMEDIATE', 'MART'].map((layer, index) => (
            <article className="transformation-model-card" key={layer}>
              <div><span>0{index + 1} · {layer}</span><StatusPill status="MISSING" /></div>
              <strong>{['stg_fed_funds_rate', 'int_fed_funds_rate_changes', 'fct_fed_funds_rate_daily'][index]}</strong>
              <code>Awaiting database connection</code>
              <p>Refresh after Studio PostgreSQL is online.</p>
              {index < 2 ? <b aria-hidden="true">→</b> : null}
            </article>
          ))}
        </div>
      </section>

      <section className="two-column-grid">
        <article className="panel compact-panel transformation-proof-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">FIRST BUILD PROOF</span><h2>Run dbt through Compose</h2></div>
            <span className="phase-badge">6.1</span>
          </div>
          <p className="rule-copy">
            dbt is intentionally outside the FastAPI Python environment. Compose starts an ephemeral
            dbt container on the same network as Studio PostgreSQL, builds the project, then removes it.
          </p>
          <pre className="transformation-command">{`docker compose -f .\\infra\\docker-compose.yml build dbt\n.\\scripts\\dbt.ps1 debug\n.\\scripts\\dbt.ps1 build`}</pre>
        </article>

        <article className="panel compact-panel transformation-proof-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">ACCEPTANCE EVIDENCE</span><h2>What green looks like</h2></div>
            <span className="rule-mark">✓</span>
          </div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Source resolves</strong><small>dbt reads mart.fed_funds_rate without duplicating ingestion ownership.</small></div></li>
            <li><span>02</span><div><strong>Three layers build</strong><small>Views land in dbt_staging and dbt_intermediate; the fact table lands in dbt_mart.</small></div></li>
            <li><span>03</span><div><strong>Fourteen tests pass</strong><small>Keys, nullability, accepted values, and rate-range assertions remain green.</small></div></li>
          </ol>
        </article>
      </section>
    </div>
  );
}

export default Transformations;
