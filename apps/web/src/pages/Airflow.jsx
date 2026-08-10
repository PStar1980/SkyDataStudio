import { useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY = {
  connection_status: 'UNAVAILABLE',
  api_version: 'v2',
  api_base_url: 'http://localhost:8080/api/v2',
  ui_url: 'http://localhost:8080',
  auth_mode: 'simple-all-admins',
  dag_count: 0,
  healthy_components: 0,
  component_count: 0,
  components: [],
  dags: [],
  error: null,
};

function Airflow() {
  const [summary, setSummary] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    getJson('/api/v1/integrations/airflow/summary', { signal: controller.signal })
      .then((payload) => {
        setSummary(payload);
        setMessage(
          payload.connection_status === 'UNAVAILABLE' && payload.error ? payload.error : '',
        );
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setSummary(EMPTY);
          setMessage(error.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [refreshKey]);

  function refreshSummary() {
    setLoading(true);
    setMessage('');
    setRefreshKey((current) => current + 1);
  }

  const pausedDags = useMemo(
    () => summary.dags.filter((dag) => dag.paused).length,
    [summary.dags],
  );

  function openAirflow() {
    window.open(summary.ui_url, '_blank', 'noopener,noreferrer');
  }

  return (
    <div className="page-stack">
      <section className="page-intro airflow-page-intro">
        <div>
          <span className="eyebrow">PHASE 5.1 · AIRFLOW RUNTIME FOUNDATION</span>
          <h1>Apache Airflow</h1>
          <p>
            Observe the isolated Airflow 3 runtime through its stable REST API. SkyData Studio
            reads orchestration state through contracts only—never through Airflow&apos;s metadata
            database.
          </p>
        </div>
        <div className="page-intro-actions">
          <button className="secondary-button" type="button" onClick={openAirflow}>
            Open Airflow UI
          </button>
          <button className="primary-button" type="button" onClick={refreshSummary} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh Airflow'}
          </button>
        </div>
      </section>

      {message ? <div className="workspace-alert error-alert">{message}</div> : null}

      <section className="airflow-metric-grid">
        <article className="metric-card">
          <span>Connection</span>
          <strong>{summary.connection_status}</strong>
          <small>Studio → Airflow REST API</small>
        </article>
        <article className="metric-card">
          <span>API Contract</span>
          <strong>{summary.api_version.toUpperCase()}</strong>
          <small>Stable public API boundary</small>
        </article>
        <article className="metric-card">
          <span>Healthy Components</span>
          <strong>{summary.healthy_components}/{summary.component_count}</strong>
          <small>Database, scheduler, DAG processor, triggerer</small>
        </article>
        <article className="metric-card">
          <span>DAGs</span>
          <strong>{summary.dag_count}</strong>
          <small>{pausedDags} paused</small>
        </article>
        <article className="metric-card">
          <span>Auth Mode</span>
          <strong>{summary.auth_mode}</strong>
          <small>Backend-owned JWT acquisition</small>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">RUNTIME STATUS</span>
            <h2>Airflow service health</h2>
          </div>
          <StatusPill status={summary.connection_status} />
        </div>
        <div className="airflow-component-grid">
          {summary.components.length ? summary.components.map((component) => (
            <article key={component.code}>
              <div>
                <span>{component.code.replaceAll('_', ' ')}</span>
                <StatusPill status={component.status} />
              </div>
              <strong>{component.label}</strong>
              <small>
                {component.latest_heartbeat
                  ? `Latest heartbeat: ${component.latest_heartbeat}`
                  : 'Health reported through /api/v2/monitor/health'}
              </small>
            </article>
          )) : (
            <div className="airflow-empty-state">
              <strong>Airflow is not reporting yet.</strong>
              <span>Start the Phase 5.1 compose services, then refresh this page.</span>
            </div>
          )}
        </div>
      </section>

      <section className="panel asset-table-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">DAG CATALOGUE</span>
            <h2>Registered Airflow workflows</h2>
          </div>
          <span className="panel-meta">{summary.dag_count} DAGs</span>
        </div>
        <div className="asset-table-scroll">
          <table className="asset-table airflow-table">
            <thead>
              <tr>
                <th>DAG</th>
                <th>Status</th>
                <th>Schedule</th>
                <th>Tags</th>
                <th>Boundary</th>
              </tr>
            </thead>
            <tbody>
              {summary.dags.length ? summary.dags.map((dag) => (
                <tr key={dag.dag_id}>
                  <td>
                    <strong className="asset-primary">{dag.display_name}</strong>
                    <code>{dag.dag_id}</code>
                    <small>{dag.description || 'No DAG description supplied.'}</small>
                  </td>
                  <td>
                    <StatusPill
                      status={dag.stale ? 'STALE' : dag.paused ? 'PAUSED' : 'ACTIVE'}
                      tone={dag.stale ? 'warning' : dag.paused ? 'scaffolded' : 'ready'}
                    />
                  </td>
                  <td>
                    <strong>{dag.timetable || 'Manual / event driven'}</strong>
                  </td>
                  <td>
                    <div className="airflow-tag-row">
                      {dag.tags.length ? dag.tags.map((tag) => <span key={tag}>{tag}</span>) : <span>—</span>}
                    </div>
                  </td>
                  <td>
                    <strong>REST API v2</strong>
                    <small>No metadata DB reads</small>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="5" className="table-empty">
                    No DAG catalogue is available yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="two-column-grid">
        <article className="panel compact-panel airflow-contract-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">ORCHESTRATION CONTRACT</span>
              <h2>Airflow owns durable batch scheduling</h2>
            </div>
            <span className="phase-badge">5.1</span>
          </div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Isolated runtime</strong><small>Airflow has its own metadata PostgreSQL database and service processes.</small></div></li>
            <li><span>02</span><div><strong>Stable API boundary</strong><small>Studio observes Airflow through authenticated REST API v2 calls only.</small></div></li>
            <li><span>03</span><div><strong>Task SDK authoring</strong><small>DAG code remains in the public airflow.sdk authoring namespace.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel airflow-next-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">NEXT PROOF</span>
              <h2>Turn the DFF pipeline into an Airflow-run batch</h2>
            </div>
            <span className="rule-mark">→</span>
          </div>
          <p className="rule-copy">
            Once this runtime/API foundation is healthy, the next slice will bind a Studio pipeline
            definition to a DAG, launch a real run, and project DAG/task evidence back into the
            workbench without replacing the proven local engine.
          </p>
          <div className="rule-footer">
            <span>Pipeline → DAG</span>
            <span>Run history</span>
            <span>Task evidence</span>
          </div>
        </article>
      </section>
    </div>
  );
}

export default Airflow;
