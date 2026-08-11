import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY_SEMANTIC_LAYER = {
  artifact_status: 'MISSING',
  generated_at: null,
  dbt_version: null,
  semantic_model_count: 0,
  metric_count: 0,
  entity_count: 0,
  dimension_count: 0,
  semantic_models: [],
  metrics: [],
};

function generatedLabel(value) {
  if (!value) return 'Awaiting semantic artifacts';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function titleCase(value) {
  if (!value) return '—';
  return value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function SemanticLayer() {
  const [summary, setSummary] = useState(EMPTY_SEMANTIC_LAYER);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadSemanticLayer = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await getJson('/api/v1/transformations/dbt/semantic'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/transformations/dbt/semantic', { signal: controller.signal })
      .then(setSummary)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const semanticReady = summary.artifact_status === 'READY';
  const metricNames = useMemo(
    () => new Set(summary.metrics.map((metric) => metric.name)),
    [summary.metrics],
  );

  return (
    <div className="page-stack semantic-layer-page">
      <section className="workspace-intro semantic-intro">
        <div>
          <span className="eyebrow">PHASE 6.3 · DBT SEMANTIC MODEL + GOVERNED METRICS</span>
          <h1>Semantic Layer</h1>
          <p>
            Keep business definitions beside the dbt mart that owns them, then project semantic
            entities, dimensions, and governed metrics from dbt artifacts without creating a
            second metadata authority inside SkyData Studio.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={loadSemanticLayer} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh Semantics'}
        </button>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <section className="metric-grid semantic-metric-grid">
        <article className="metric-card">
          <span>Artifacts</span>
          <strong>{summary.artifact_status}</strong>
          <small>{generatedLabel(summary.generated_at)}</small>
        </article>
        <article className="metric-card">
          <span>Semantic Models</span>
          <strong>{summary.semantic_model_count}</strong>
          <small>{semanticReady ? 'Governed model graph discovered' : 'Run dbt build to refresh semantics'}</small>
        </article>
        <article className="metric-card">
          <span>Governed Metrics</span>
          <strong>{summary.metric_count}</strong>
          <small>Simple metrics owned by dbt</small>
        </article>
        <article className="metric-card">
          <span>Dimensions</span>
          <strong>{summary.dimension_count}</strong>
          <small>{summary.entity_count} semantic entity</small>
        </article>
        <article className="metric-card">
          <span>dbt Core</span>
          <strong>{summary.dbt_version || '—'}</strong>
          <small>Artifact-producing runtime</small>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">SEMANTIC MODEL GRAPH</span>
            <h2>Governed mart → entity + dimensions → reusable metrics</h2>
          </div>
          <StatusPill status={semanticReady ? 'READY' : summary.artifact_status} />
        </div>

        {summary.semantic_models.length ? (
          <div className="semantic-model-grid">
            {summary.semantic_models.map((model) => (
              <article className="semantic-model-card" key={model.unique_id}>
                <div className="semantic-model-heading">
                  <div>
                    <span>SEMANTIC MODEL</span>
                    <strong>{model.name}</strong>
                    <code>{model.relation || 'relation pending'}</code>
                  </div>
                  <StatusPill status="READY" />
                </div>
                <p>{model.description || 'Semantic annotations owned by the dbt mart model.'}</p>
                <div className="semantic-contract-grid">
                  <div>
                    <span>PRIMARY ENTITY</span>
                    <strong>{model.entities.find((entity) => entity.entity_type === 'PRIMARY')?.name || '—'}</strong>
                    <small>{model.entities.find((entity) => entity.entity_type === 'PRIMARY')?.expression || 'model column'}</small>
                  </div>
                  <div>
                    <span>DEFAULT TIME</span>
                    <strong>{model.default_time_dimension || '—'}</strong>
                    <small>Metric aggregation seam</small>
                  </div>
                  <div>
                    <span>METRICS</span>
                    <strong>{model.metric_names.filter((name) => metricNames.has(name)).length}</strong>
                    <small>Governed definitions</small>
                  </div>
                </div>
                <div className="semantic-definition-block">
                  <span>Dimensions</span>
                  <div className="semantic-chip-list">
                    {model.dimensions.map((dimension) => (
                      <span key={`${model.unique_id}-${dimension.name}`}>
                        <strong>{dimension.name}</strong>
                        <small>{titleCase(dimension.dimension_type)}{dimension.granularity ? ` · ${dimension.granularity.toLowerCase()}` : ''}</small>
                      </span>
                    ))}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="semantic-empty">
            <strong>No semantic model artifacts are available yet.</strong>
            <span>Run <code>.\scripts\dbt.ps1 build</code>, then refresh this page.</span>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">METRIC CATALOGUE</span>
            <h2>Business measures defined once, beside the model</h2>
          </div>
          <span className="panel-count">{summary.metrics.length} metrics</span>
        </div>
        {summary.metrics.length ? (
          <div className="semantic-metric-list">
            {summary.metrics.map((metric) => (
              <article className="semantic-metric-card" key={metric.unique_id}>
                <header>
                  <div>
                    <span>{titleCase(metric.metric_type)}</span>
                    <h3>{metric.label}</h3>
                    <code>{metric.name}</code>
                  </div>
                  <StatusPill status="READY" />
                </header>
                <p>{metric.description || 'Governed dbt metric.'}</p>
                <dl>
                  <div><dt>Aggregation</dt><dd>{metric.aggregation || '—'}</dd></div>
                  <div><dt>Expression</dt><dd>{metric.expression || '—'}</dd></div>
                  <div><dt>Time</dt><dd>{metric.time_dimension || '—'}</dd></div>
                  <div><dt>Semantic model</dt><dd>{metric.semantic_model || '—'}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <div className="semantic-empty">
            <strong>No governed metrics discovered.</strong>
            <span>The dbt manifest will become the runtime evidence after the next semantic build.</span>
          </div>
        )}
      </section>

      <section className="two-column-grid semantic-proof-grid">
        <article className="panel compact-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">ACCEPTANCE CONTRACT</span><h2>What Phase 6.3 proves</h2></div>
            <span className="phase-badge">6.3</span>
          </div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>One primary entity</strong><small>Daily observations have a stable semantic key.</small></div></li>
            <li><span>02</span><div><strong>Reusable dimensions</strong><small>Time and direction cuts are governed beside the mart.</small></div></li>
            <li><span>03</span><div><strong>Four metrics</strong><small>Average, minimum, maximum, and observation count share one definition seam.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">BOUNDARY</span><h2>Definitions, not a hosted metric service</h2></div>
            <span className="rule-mark">∑</span>
          </div>
          <p className="rule-copy">
            Phase 6.3 proves portable dbt semantic definitions and artifact evidence. SkyData Studio
            does not pretend to be a hosted dbt Semantic Layer query service; downstream execution
            stays a later integration boundary.
          </p>
          <div className="rule-footer"><span>One authority</span><span>Portable metrics</span><span>Artifact proof</span></div>
        </article>
      </section>
    </div>
  );
}

export default SemanticLayer;
