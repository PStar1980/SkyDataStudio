import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from './StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY = {
  consumer_status: 'MISSING',
  semantic_artifact_status: 'MISSING',
  consumer_contract_count: 0,
  resolved_consumer_count: 0,
  declared_metric_count: 0,
  resolved_metric_count: 0,
  unresolved_metric_count: 0,
  node_count: 0,
  edge_count: 0,
  source_paths: [],
  consumers: [],
  metric_bindings: [],
  nodes: [],
  edges: [],
  default_impact: {
    selected_metric_name: null,
    selected_metric_label: null,
    downstream_consumer_count: 0,
    consumers: [],
  },
};

function consumerTone(status) {
  if (status === 'READY') return 'READY';
  if (status === 'PARTIAL') return 'WARNING';
  return 'PLANNED';
}

function ConsumerLineagePanel() {
  const [summary, setSummary] = useState(EMPTY);
  const [impact, setImpact] = useState(EMPTY.default_impact);
  const [loading, setLoading] = useState(true);
  const [impactLoading, setImpactLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await getJson('/api/v1/lineage/consumers/summary');
      setSummary(payload);
      setImpact(payload.default_impact || EMPTY.default_impact);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/lineage/consumers/summary', { signal: controller.signal })
      .then((payload) => {
        setSummary(payload);
        setImpact(payload.default_impact || EMPTY.default_impact);
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const metricNodes = useMemo(
    () => summary.nodes.filter((node) => node.node_type === 'METRIC'),
    [summary.nodes],
  );
  const consumerNodes = useMemo(
    () => summary.nodes.filter((node) => node.node_type === 'ANALYTICS_CONSUMER'),
    [summary.nodes],
  );

  async function selectMetric(node) {
    const metricName = node.metadata.metric_name;
    if (!metricName) return;
    setImpactLoading(true);
    setError('');
    try {
      setImpact(await getJson(
        `/api/v1/lineage/consumers/impact?metricName=${encodeURIComponent(metricName)}`,
      ));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setImpactLoading(false);
    }
  }

  return (
    <section className="panel consumer-lineage-panel">
      <div className="panel-heading consumer-lineage-heading">
        <div>
          <span className="eyebrow">PHASE 8.5 · ANALYTICS CONSUMER LINEAGE</span>
          <h2>Governed metrics terminate at declared consumers</h2>
          <p>
            Resolve source-controlled report dependencies against dbt semantic artifacts without
            claiming a Power BI deployment that Phase 10 has not provisioned yet.
          </p>
        </div>
        <div className="consumer-lineage-actions">
          <StatusPill status={summary.consumer_status} tone={consumerTone(summary.consumer_status)} />
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh Consumers'}
          </button>
        </div>
      </div>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <div className="consumer-lineage-metrics">
        <div><span>CONSUMERS</span><strong>{summary.resolved_consumer_count}/{summary.consumer_contract_count}</strong><small>source-controlled declarations</small></div>
        <div><span>METRICS</span><strong>{summary.resolved_metric_count}/{summary.declared_metric_count}</strong><small>{summary.unresolved_metric_count} unresolved</small></div>
        <div><span>SEMANTIC</span><strong>{summary.semantic_artifact_status}</strong><small>dbt-owned evidence</small></div>
        <div><span>GRAPH</span><strong>{summary.node_count}</strong><small>{summary.edge_count} consumer edges</small></div>
      </div>

      <div className="consumer-lineage-grid">
        <article className="consumer-lineage-group">
          <header><span>GOVERNED METRICS</span><strong>Select a metric to inspect consumers</strong></header>
          <div className="consumer-metric-list">
            {metricNodes.map((node) => (
              <button
                key={node.id}
                type="button"
                className={impact.selected_metric_name === node.metadata.metric_name ? 'is-selected' : ''}
                onClick={() => selectMetric(node)}
              >
                <span>{node.metadata.metric_type || 'METRIC'}</span>
                <strong>{node.label}</strong>
              </button>
            ))}
          </div>
        </article>

        <article className="consumer-lineage-group">
          <header><span>DECLARED CONSUMERS</span><strong>Reporting dependency contracts</strong></header>
          <div className="consumer-report-list">
            {consumerNodes.map((node) => (
              <div key={node.id}>
                <span>{node.metadata.consumer_type || 'CONSUMER'}</span>
                <strong>{node.label}</strong>
                <small>{node.system} · {node.metadata.deployment_status || node.status}</small>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="consumer-impact-strip">
        <div>
          <span>SELECTED METRIC</span>
          <strong>{impact.selected_metric_label || 'No metric selected'}</strong>
        </div>
        <div>
          <span>DOWNSTREAM CONSUMERS</span>
          <strong>{impactLoading ? '…' : impact.downstream_consumer_count}</strong>
        </div>
        <div>
          <span>DELIVERY BOUNDARY</span>
          <strong>DECLARATION ONLY</strong>
        </div>
      </div>

      <div className="consumer-lineage-edge-strip">
        {summary.edges.map((edge) => (
          <span key={edge.id}><b>{edge.edge_type}</b>{edge.label}</span>
        ))}
      </div>
    </section>
  );
}

export default ConsumerLineagePanel;
