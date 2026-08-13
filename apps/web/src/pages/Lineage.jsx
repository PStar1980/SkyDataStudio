import { useCallback, useEffect, useMemo, useState } from 'react';
import FieldLineagePanel from '../components/FieldLineagePanel.jsx';
import StatusPill from '../components/StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY_IMPACT = {
  selected_node_id: null,
  selected_node_label: null,
  downstream_node_count: 0,
  affected_model_count: 0,
  affected_semantic_model_count: 0,
  affected_metric_count: 0,
  affected_layers: [],
  nodes: [],
};

const EMPTY = {
  artifact_status: 'MISSING',
  metadata_mapping_count: 0,
  dbt_model_count: 0,
  semantic_model_count: 0,
  metric_count: 0,
  node_count: 0,
  edge_count: 0,
  nodes: [],
  edges: [],
  default_impact: EMPTY_IMPACT,
};

function nodeOrder(node) {
  if (node.node_type === 'SOURCE_ASSET') return 1;
  if (node.node_type === 'CURATED_ASSET') return 2;
  if (node.node_type === 'DBT_SOURCE') return 3;
  if (node.node_type === 'DBT_MODEL' && node.layer === 'STAGING') return 4;
  if (node.node_type === 'DBT_MODEL' && node.layer === 'INTERMEDIATE') return 5;
  if (node.node_type === 'DBT_MODEL' && node.layer === 'MART') return 6;
  if (node.node_type === 'SEMANTIC_MODEL') return 7;
  if (node.node_type === 'METRIC') return 8;
  return 99;
}

function statusTone(status) {
  if (status === 'READY') return 'READY';
  if (status === 'PARTIAL') return 'WARNING';
  return 'PLANNED';
}

function nodeKind(node) {
  if (node.node_type === 'SOURCE_ASSET') return 'Source asset';
  if (node.node_type === 'CURATED_ASSET') return 'Studio curated';
  if (node.node_type === 'DBT_SOURCE') return 'dbt source';
  if (node.node_type === 'DBT_MODEL') return 'dbt model';
  if (node.node_type === 'SEMANTIC_MODEL') return 'Semantic model';
  return 'Governed metric';
}

function Lineage() {
  const [summary, setSummary] = useState(EMPTY);
  const [impact, setImpact] = useState(EMPTY_IMPACT);
  const [loading, setLoading] = useState(true);
  const [impactLoading, setImpactLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await getJson('/api/v1/lineage/summary');
      setSummary(payload);
      setImpact(payload.default_impact || EMPTY_IMPACT);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/lineage/summary', { signal: controller.signal })
      .then((payload) => {
        setSummary(payload);
        setImpact(payload.default_impact || EMPTY_IMPACT);
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const orderedNodes = useMemo(
    () => [...summary.nodes].sort((left, right) => (
      nodeOrder(left) - nodeOrder(right) || left.label.localeCompare(right.label)
    )),
    [summary.nodes],
  );

  const impactedIds = useMemo(
    () => new Set((impact.nodes || []).map((node) => node.id)),
    [impact.nodes],
  );

  async function selectNode(node) {
    setImpactLoading(true);
    setError('');
    try {
      setImpact(await getJson(`/api/v1/lineage/impact?nodeId=${encodeURIComponent(node.id)}`));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setImpactLoading(false);
    }
  }

  return (
    <div className="page-stack lineage-page">
      <section className="workspace-intro lineage-intro">
        <div>
          <span className="eyebrow">PHASE 8.2 · FIELD-LEVEL LINEAGE + COLUMN IMPACT</span>
          <h1>Lineage & Impact</h1>
          <p>
            Keep the federated asset graph from Phase 8.1, then trace field-level impact from registered
            mappings through dbt derivations and into governed metrics before a schema change lands.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={load} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh Lineage'}
        </button>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <section className="metric-grid lineage-metric-grid">
        <article className="metric-card"><span>Graph</span><strong>{summary.artifact_status}</strong><small>Federated evidence posture</small></article>
        <article className="metric-card"><span>Nodes</span><strong>{summary.node_count}</strong><small>{summary.edge_count} directed edges</small></article>
        <article className="metric-card"><span>dbt Models</span><strong>{summary.dbt_model_count}</strong><small>Artifact-backed transformations</small></article>
        <article className="metric-card"><span>Semantic</span><strong>{summary.semantic_model_count}</strong><small>Governed semantic models</small></article>
        <article className="metric-card"><span>Metrics</span><strong>{summary.metric_count}</strong><small>Downstream business measures</small></article>
      </section>

      <section className="panel lineage-graph-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">FEDERATED LINEAGE GRAPH</span>
            <h2>SkyCommand source → Studio mart → dbt → semantic delivery</h2>
          </div>
          <StatusPill status={summary.artifact_status} tone={statusTone(summary.artifact_status)} />
        </div>
        {orderedNodes.length ? (
          <div className="lineage-flow">
            {orderedNodes.map((node) => {
              const selected = impact.selected_node_id === node.id;
              const impacted = impactedIds.has(node.id);
              return (
                <button
                  className={`lineage-node ${selected ? 'is-selected' : ''} ${impacted ? 'is-impacted' : ''}`}
                  key={node.id}
                  type="button"
                  onClick={() => selectNode(node)}
                >
                  <span className="lineage-node-top"><b>{node.layer}</b><StatusPill status={node.status} /></span>
                  <strong>{node.label}</strong>
                  <small>{nodeKind(node)} · {node.system}</small>
                  {node.relation ? <code>{node.relation}</code> : null}
                </button>
              );
            })}
          </div>
        ) : (
          <div className="data-model-empty">
            <strong>No lineage evidence is available yet.</strong>
            <span>Register a source mapping and run <code>.\scripts\dbt.ps1 build</code>.</span>
          </div>
        )}
        <div className="lineage-edge-strip">
          {summary.edges.map((edge) => (
            <span key={edge.id}><b>{edge.edge_type}</b>{edge.label}</span>
          ))}
        </div>
      </section>

      <section className="two-column-grid lineage-impact-grid">
        <article className="panel compact-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">CHANGE IMPACT</span><h2>{impact.selected_node_label || 'Select a node'}</h2></div>
            <span className="phase-badge">8.1</span>
          </div>
          <div className="lineage-impact-metrics">
            <div><span>DOWNSTREAM</span><strong>{impact.downstream_node_count}</strong></div>
            <div><span>MODELS</span><strong>{impact.affected_model_count}</strong></div>
            <div><span>SEMANTIC</span><strong>{impact.affected_semantic_model_count}</strong></div>
            <div><span>METRICS</span><strong>{impact.affected_metric_count}</strong></div>
          </div>
          <p className="lineage-impact-copy">
            {impactLoading
              ? 'Recomputing downstream radius…'
              : impact.downstream_node_count
                ? `A change here can flow through ${impact.affected_layers.join(' → ')}.`
                : 'This node has no downstream nodes in the current graph.'}
          </p>
        </article>

        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">IMPACTED INVENTORY</span><h2>Downstream nodes</h2></div><span className="panel-meta">{impact.nodes.length} affected</span></div>
          <div className="lineage-impact-list">
            {impact.nodes.map((node) => (
              <div key={node.id}><span>{node.layer}</span><strong>{node.label}</strong><small>{nodeKind(node)}</small></div>
            ))}
            {!impact.nodes.length ? <p>No downstream impact for the selected node.</p> : null}
          </div>
        </article>
      </section>

      <FieldLineagePanel />

      <section className="two-column-grid">
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">ACCEPTANCE CONTRACT</span><h2>What Phase 8.2 proves</h2></div><span className="phase-badge">8.2</span></div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Field mappings stay authoritative</strong><small>Studio reuses the two registered source-to-target field maps rather than reconstructing ingestion semantics.</small></div></li>
            <li><span>02</span><div><strong>dbt owns derived columns</strong><small>Column lineage declarations live beside dbt models and are carried through the generated manifest.</small></div></li>
            <li><span>03</span><div><strong>Metrics become field consumers</strong><small>Metric expressions connect mart fields to business measures so field-level downstream impact is explicit.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">BOUNDARY</span><h2>Read the graph; do not rewrite it</h2></div><span className="rule-mark">⌁</span></div>
          <p className="rule-copy">
            Phase 8.2 remains a federated read model. Studio does not infer arbitrary SQL or persist a second lineage store; mapping fields, dbt column annotations, and metric expressions stay at their existing authorities. Quality overlays and consumer/report lineage remain later Phase 8 slices.
          </p>
          <div className="rule-footer"><span>Federated evidence</span><span>Directed impact</span><span>No duplicate authority</span></div>
        </article>
      </section>
    </div>
  );
}

export default Lineage;
