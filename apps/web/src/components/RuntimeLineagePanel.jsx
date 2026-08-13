import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from './StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY = {
  runtime_status: 'MISSING',
  airflow_connection_status: 'UNKNOWN',
  pipeline_code: 'FED_FUNDS_RATE_PIPELINE',
  dag_id: 'skydata_studio_fed_funds_rate_pipeline',
  dag_run_id: null,
  studio_run_id: null,
  studio_run_key: null,
  airflow_dag_run_status: null,
  studio_run_status: null,
  airflow_task_count: 0,
  successful_airflow_task_count: 0,
  studio_step_count: 0,
  succeeded_studio_step_count: 0,
  replay_count: 0,
  materialization_executed: false,
  data_mutation_applied: false,
  target_relation: null,
  target_row_count: null,
  airflow_error: null,
  node_count: 0,
  edge_count: 0,
  nodes: [],
  edges: [],
};

function runtimeTone(status) {
  if (status === 'READY' || status === 'SUCCEEDED' || status === 'success') return 'READY';
  if (status === 'PARTIAL' || status === 'UNKNOWN') return 'WARNING';
  return status;
}

function RuntimeLineagePanel() {
  const [summary, setSummary] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await getJson('/api/v1/lineage/runtime/summary'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/lineage/runtime/summary', { signal: controller.signal })
      .then((payload) => setSummary(payload))
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const groups = useMemo(() => {
    const structural = summary.nodes.filter((node) => node.node_type === 'STRUCTURAL_ASSET');
    const airflow = summary.nodes.filter((node) => node.node_type.startsWith('AIRFLOW_'));
    const studio = summary.nodes.filter((node) => (
      node.node_type === 'PIPELINE_DEFINITION'
      || node.node_type === 'STUDIO_PIPELINE_RUN'
      || node.node_type === 'STUDIO_STEP_RUN'
    ));
    return { structural, airflow, studio };
  }, [summary.nodes]);

  return (
    <section className="panel runtime-lineage-panel">
      <div className="panel-heading runtime-lineage-heading">
        <div>
          <span className="eyebrow">PHASE 8.4 · PIPELINE + AIRFLOW EXECUTION LINEAGE</span>
          <h2>Runtime evidence joins the structural graph</h2>
          <p>
            Link the latest replay-safe Airflow DAG run to the Studio pipeline run, its four
            materialization steps, and the same source and curated target nodes used by design lineage.
          </p>
        </div>
        <div className="runtime-lineage-actions">
          <StatusPill status={summary.runtime_status} tone={runtimeTone(summary.runtime_status)} />
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh Runtime'}
          </button>
        </div>
      </div>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}
      {summary.airflow_error ? (
        <div className="workspace-alert error-alert">{summary.airflow_error}</div>
      ) : null}

      <div className="runtime-lineage-metrics">
        <div><span>RUNTIME</span><strong>{summary.runtime_status}</strong><small>{summary.node_count} nodes · {summary.edge_count} edges</small></div>
        <div><span>AIRFLOW TASKS</span><strong>{summary.successful_airflow_task_count}/{summary.airflow_task_count}</strong><small>{summary.airflow_dag_run_status || 'No live DAG run'}</small></div>
        <div><span>STUDIO STEPS</span><strong>{summary.succeeded_studio_step_count}/{summary.studio_step_count}</strong><small>{summary.studio_run_status || 'No linked run'}</small></div>
        <div><span>REPLAYS</span><strong>{summary.replay_count}</strong><small>same logical AIRFLOW run key</small></div>
        <div><span>MATERIALIZATION</span><strong>{summary.materialization_executed ? 'PROVEN' : 'PENDING'}</strong><small>{summary.target_row_count ?? '—'} target rows</small></div>
      </div>

      <div className="runtime-lineage-grid">
        <article className="runtime-lineage-group">
          <header><div><span>STRUCTURAL SEAM</span><strong>Source and curated target</strong></div><b>{groups.structural.length}</b></header>
          <div className="runtime-lineage-list">
            {groups.structural.map((node) => (
              <div key={node.id}><span>{node.metadata.role || 'ASSET'}</span><strong>{node.label}</strong><small>{node.relation || node.system}</small></div>
            ))}
          </div>
        </article>
        <article className="runtime-lineage-group">
          <header><div><span>AIRFLOW CONTROL PLANE</span><strong>DAG and task execution</strong></div><b>{groups.airflow.length}</b></header>
          <div className="runtime-lineage-list runtime-lineage-scroll">
            {groups.airflow.map((node) => (
              <div key={node.id}><span>{node.node_type.replaceAll('_', ' ')}</span><strong>{node.label}</strong><small>{node.status} · try {node.metadata.try_number ?? '—'}</small></div>
            ))}
          </div>
        </article>
        <article className="runtime-lineage-group">
          <header><div><span>STUDIO EXECUTION</span><strong>Pipeline and step evidence</strong></div><b>{groups.studio.length}</b></header>
          <div className="runtime-lineage-list runtime-lineage-scroll">
            {groups.studio.map((node) => (
              <div key={node.id}><span>{node.node_type.replaceAll('_', ' ')}</span><strong>{node.label}</strong><small>{node.status} · {node.metadata.step_type || node.metadata.pipeline_code || node.system}</small></div>
            ))}
          </div>
        </article>
      </div>

      <div className="runtime-lineage-edge-strip">
        {summary.edges.map((edge) => (
          <span key={edge.id}><b>{edge.edge_type}</b>{edge.label}</span>
        ))}
      </div>

      <div className="runtime-lineage-contract">
        <div><span>DAG RUN</span><strong>{summary.dag_run_id || 'No linked Airflow execution'}</strong></div>
        <div><span>STUDIO RUN KEY</span><strong>{summary.studio_run_key || '—'}</strong></div>
        <div><span>TARGET</span><strong>{summary.target_relation || '—'}</strong></div>
        <div><span>MUTATION</span><strong>{summary.data_mutation_applied ? 'CHANGED' : 'IDEMPOTENT'}</strong></div>
      </div>
    </section>
  );
}

export default RuntimeLineagePanel;
