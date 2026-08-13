import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from './StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY_IMPACT = {
  selected_field_id: null,
  selected_field_label: null,
  downstream_node_count: 0,
  affected_field_count: 0,
  affected_metric_count: 0,
  affected_relations: [],
  affected_layers: [],
  nodes: [],
};

const EMPTY = {
  artifact_status: 'MISSING',
  field_mapping_count: 0,
  dbt_annotated_column_count: 0,
  metric_binding_count: 0,
  node_count: 0,
  edge_count: 0,
  nodes: [],
  edges: [],
  default_impact: EMPTY_IMPACT,
};

function fieldOrder(node) {
  if (node.node_type === 'SOURCE_FIELD') return 1;
  if (node.node_type === 'CURATED_FIELD') return 2;
  if (node.node_type === 'DBT_SOURCE_FIELD') return 3;
  if (node.layer === 'STAGING') return 4;
  if (node.layer === 'INTERMEDIATE') return 5;
  if (node.layer === 'MART') return 6;
  if (node.node_type === 'METRIC') return 7;
  return 99;
}

function statusTone(status) {
  if (status === 'READY') return 'READY';
  if (status === 'PARTIAL') return 'WARNING';
  return 'PLANNED';
}

function fieldKind(node) {
  if (node.node_type === 'SOURCE_FIELD') return 'Source field';
  if (node.node_type === 'CURATED_FIELD') return 'Curated field';
  if (node.node_type === 'DBT_SOURCE_FIELD') return 'dbt source field';
  if (node.node_type === 'DBT_MODEL_FIELD') return 'dbt model field';
  return 'Governed metric';
}

function FieldLineagePanel() {
  const [summary, setSummary] = useState(EMPTY);
  const [impact, setImpact] = useState(EMPTY_IMPACT);
  const [loading, setLoading] = useState(true);
  const [impactLoading, setImpactLoading] = useState(false);
  const [error, setError] = useState('');

  const applySummary = useCallback((payload) => {
    setSummary(payload);
    setImpact(payload.default_impact || EMPTY_IMPACT);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      applySummary(await getJson('/api/v1/lineage/fields/summary'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [applySummary]);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/lineage/fields/summary', { signal: controller.signal })
      .then(applySummary)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [applySummary]);

  const groups = useMemo(() => {
    const grouped = new Map();
    [...summary.nodes]
      .sort((left, right) => (
        fieldOrder(left) - fieldOrder(right) || left.label.localeCompare(right.label)
      ))
      .forEach((node) => {
        const parent = node.parent_label || node.relation || node.layer;
        const key = `${fieldOrder(node)}:${parent}`;
        const current = grouped.get(key) || { key, label: parent, layer: node.layer, nodes: [] };
        current.nodes.push(node);
        grouped.set(key, current);
      });
    return [...grouped.values()];
  }, [summary.nodes]);

  const impactedIds = useMemo(
    () => new Set((impact.nodes || []).map((node) => node.id)),
    [impact.nodes],
  );

  async function selectField(node) {
    setImpactLoading(true);
    setError('');
    try {
      const path = `/api/v1/lineage/fields/impact?fieldId=${encodeURIComponent(node.id)}`;
      setImpact(await getJson(path));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setImpactLoading(false);
    }
  }

  return (
    <>
      <section className="panel field-lineage-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">FIELD LINEAGE · PHASE 8.2</span>
            <h2>DFF fields → curated columns → dbt derivations → governed metrics</h2>
          </div>
          <div className="field-lineage-actions">
            <StatusPill status={summary.artifact_status} tone={statusTone(summary.artifact_status)} />
            <button className="secondary-button" type="button" onClick={load} disabled={loading}>
              {loading ? 'Refreshing…' : 'Refresh Fields'}
            </button>
          </div>
        </div>

        {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

        <div className="field-lineage-metrics">
          <div><span>FIELD NODES</span><strong>{summary.node_count}</strong><small>{summary.edge_count} directed edges</small></div>
          <div><span>FIELD MAPS</span><strong>{summary.field_mapping_count}</strong><small>Studio mapping evidence</small></div>
          <div><span>DBT COLUMNS</span><strong>{summary.dbt_annotated_column_count}</strong><small>Manifest annotations</small></div>
          <div><span>METRIC BINDINGS</span><strong>{summary.metric_binding_count}</strong><small>Mart field consumers</small></div>
        </div>

        {groups.length ? (
          <div className="field-lineage-groups">
            {groups.map((group) => (
              <article className="field-lineage-group" key={group.key}>
                <header><span>{group.layer}</span><strong>{group.label}</strong></header>
                <div className="field-lineage-items">
                  {group.nodes.map((node) => {
                    const selected = impact.selected_field_id === node.id;
                    const impacted = impactedIds.has(node.id);
                    return (
                      <button
                        className={`field-lineage-node ${selected ? 'is-selected' : ''} ${impacted ? 'is-impacted' : ''}`}
                        key={node.id}
                        type="button"
                        onClick={() => selectField(node)}
                      >
                        <strong>{node.field_name}</strong>
                        <small>{fieldKind(node)}</small>
                      </button>
                    );
                  })}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="data-model-empty">
            <strong>No field-level lineage annotations are available yet.</strong>
            <span>Run <code>.\scripts\dbt.ps1 build</code> to regenerate the dbt manifest.</span>
          </div>
        )}
      </section>

      <section className="two-column-grid lineage-impact-grid">
        <article className="panel compact-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">FIELD IMPACT RADIUS</span><h2>{impact.selected_field_label || 'Select a field'}</h2></div>
            <span className="phase-badge">8.2</span>
          </div>
          <div className="lineage-impact-metrics">
            <div><span>DOWNSTREAM</span><strong>{impact.downstream_node_count}</strong></div>
            <div><span>FIELDS</span><strong>{impact.affected_field_count}</strong></div>
            <div><span>METRICS</span><strong>{impact.affected_metric_count}</strong></div>
            <div><span>RELATIONS</span><strong>{impact.affected_relations.length}</strong></div>
          </div>
          <p className="lineage-impact-copy">
            {impactLoading
              ? 'Tracing column-level impact…'
              : impact.downstream_node_count
                ? `This field can affect ${impact.affected_layers.join(' → ')}.`
                : 'This field has no downstream consumers in the current graph.'}
          </p>
        </article>

        <article className="panel compact-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">FIELD IMPACT INVENTORY</span><h2>Dependent fields and metrics</h2></div>
            <span className="panel-meta">{impact.nodes.length} affected</span>
          </div>
          <div className="lineage-impact-list field-impact-list">
            {impact.nodes.map((node) => (
              <div key={node.id}><span>{node.layer}</span><strong>{node.label}</strong><small>{fieldKind(node)}</small></div>
            ))}
            {!impact.nodes.length ? <p>No downstream field impact for the selected field.</p> : null}
          </div>
        </article>
      </section>
    </>
  );
}

export default FieldLineagePanel;
