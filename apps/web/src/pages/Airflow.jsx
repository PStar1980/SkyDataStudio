import { useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson, postJson } from '../services/api.js';

const PROOF_DAG_ID = 'skydata_studio_fed_funds_rate_pipeline';

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

const EMPTY_RUNS = {
  dag_id: PROOF_DAG_ID,
  total: 0,
  items: [],
};

const EMPTY_INGESTION_EVENT = {
  dag_id: PROOF_DAG_ID,
  asset_uri: 'x-skycommand://ingestion/macro/dff',
  asset_registered: false,
  eligible: false,
  already_emitted: false,
  ingestion_run: null,
  event: null,
  message: 'Waiting for SkyCommand ingestion evidence.',
};

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function Airflow() {
  const [summary, setSummary] = useState(EMPTY);
  const [runs, setRuns] = useState(EMPTY_RUNS);
  const [selectedRun, setSelectedRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runsLoading, setRunsLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [eventLoading, setEventLoading] = useState(true);
  const [eventLaunching, setEventLaunching] = useState(false);
  const [ingestionEvent, setIngestionEvent] = useState(EMPTY_INGESTION_EVENT);
  const [message, setMessage] = useState('');
  const [runMessage, setRunMessage] = useState('');
  const [eventMessage, setEventMessage] = useState('');
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

  useEffect(() => {
    const controller = new AbortController();

    getJson(`/api/v1/integrations/airflow/dags/${PROOF_DAG_ID}/runs?limit=20`, {
      signal: controller.signal,
    })
      .then((payload) => {
        setRuns(payload);
        setRunMessage('');
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setRuns(EMPTY_RUNS);
          setRunMessage(error.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setRunsLoading(false);
      });

    return () => controller.abort();
  }, [refreshKey]);

  useEffect(() => {
    const controller = new AbortController();

    getJson(
      `/api/v1/integrations/airflow/dags/${PROOF_DAG_ID}/ingestion-events/latest`,
      { signal: controller.signal },
    )
      .then((payload) => {
        setIngestionEvent(payload);
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setIngestionEvent(EMPTY_INGESTION_EVENT);
          setEventMessage(error.message);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setEventLoading(false);
      });

    return () => controller.abort();
  }, [refreshKey]);

  const pausedDags = useMemo(
    () => summary.dags.filter((dag) => dag.paused).length,
    [summary.dags],
  );

  const proofDag = useMemo(
    () => summary.dags.find((dag) => dag.dag_id === PROOF_DAG_ID),
    [summary.dags],
  );

  function refreshSummary() {
    setLoading(true);
    setRunsLoading(true);
    setEventLoading(true);
    setMessage('');
    setRunMessage('');
    setEventMessage('');
    setRefreshKey((current) => current + 1);
  }

  function openAirflow() {
    window.open(summary.ui_url, '_blank', 'noopener,noreferrer');
  }

  function launchBatch() {
    setLaunching(true);
    setRunMessage('');
    postJson(`/api/v1/integrations/airflow/dags/${PROOF_DAG_ID}/runs`, {
      pipeline_code: 'FED_FUNDS_RATE_PIPELINE',
    })
      .then((payload) => {
        setRunMessage(`Airflow run ${payload.run.dag_run_id} was queued successfully.`);
        setRunsLoading(true);
        setSelectedRun(null);
        setRefreshKey((current) => current + 1);
      })
      .catch((error) => setRunMessage(error.message))
      .finally(() => setLaunching(false));
  }

  function launchIngestionEvent() {
    setEventLaunching(true);
    setEventMessage('');
    const ingestionRunId = ingestionEvent.ingestion_run?.ingestion_run_id;

    postJson(`/api/v1/integrations/airflow/dags/${PROOF_DAG_ID}/ingestion-events`, {
      ingestion_run_id: ingestionRunId || null,
      domain_code: 'MACRO',
      source_code: 'FRED',
      asset_code: 'DFF',
      pipeline_code: 'FED_FUNDS_RATE_PIPELINE',
    })
      .then((payload) => {
        const runIds = payload.event.created_dag_run_ids || [];
        const createdRun = runIds.length ? ` and created DAG run ${runIds[0]}` : '';
        setEventMessage(
          payload.reused
            ? `SkyCommand ingestion run ${payload.ingestion_run.ingestion_run_id} already has asset event #${payload.event.id}; the signal was safely reused.`
            : `Airflow asset event #${payload.event.id} was emitted for SkyCommand ingestion run ${payload.ingestion_run.ingestion_run_id}${createdRun}.`,
        );
        setRunsLoading(true);
        setSelectedRun(null);
        setEventLoading(true);
        setRefreshKey((current) => current + 1);
      })
      .catch((error) => setEventMessage(error.message))
      .finally(() => setEventLaunching(false));
  }

  function inspectRun(dagRunId) {
    setRunMessage('');
    getJson(`/api/v1/integrations/airflow/dags/${PROOF_DAG_ID}/runs/${encodeURIComponent(dagRunId)}`)
      .then((payload) => setSelectedRun(payload))
      .catch((error) => setRunMessage(error.message));
  }

  return (
    <div className="page-stack">
      <section className="page-intro airflow-page-intro">
        <div>
          <span className="eyebrow">PHASE 5.4 · INGESTION-COMPLETE EVENT TRIGGER</span>
          <h1>Apache Airflow</h1>
          <p>
            Observe the isolated Airflow runtime, launch the governed Federal Funds Rate batch,
            and push a SkyCommand ingestion-complete signal into Airflow as a native asset event
            while preserving the same replay-safe Studio execution contract.
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
          <span>DFF Batch</span>
          <strong>{proofDag ? (proofDag.paused ? 'PAUSED' : 'READY') : 'WAITING'}</strong>
          <small>{runs.total} observed run{runs.total === 1 ? '' : 's'}</small>
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
              <span>Start the Phase 5 compose services, then refresh this page.</span>
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
                  <td><strong>{dag.timetable || 'Manual / event driven'}</strong></td>
                  <td>
                    <div className="airflow-tag-row">
                      {dag.tags.length ? dag.tags.map((tag) => <span key={tag}>{tag}</span>) : <span>—</span>}
                    </div>
                  </td>
                  <td><strong>REST API v2</strong><small>No metadata DB reads</small></td>
                </tr>
              )) : (
                <tr><td colSpan="5" className="table-empty">No DAG catalogue is available yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel asset-table-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">PIPELINE → DAG</span>
            <h2>Federal Funds Rate durable batch proof</h2>
            <p className="rule-copy">
              Airflow owns orchestration; the existing Studio local engine keeps replay, mapping,
              validation, and mart materialization authority.
            </p>
          </div>
          <button
            className="primary-button"
            type="button"
            onClick={launchBatch}
            disabled={launching || proofDag?.paused || !proofDag}
          >
            {launching ? 'Launching…' : 'Launch DFF Batch'}
          </button>
        </div>
        {runMessage ? <div className="workspace-alert">{runMessage}</div> : null}
        <div className="rule-footer">
          <span>FED_FUNDS_RATE_PIPELINE</span>
          <span>{PROOF_DAG_ID}</span>
          <span>Replay-safe callback</span>
        </div>
        <div className="asset-table-scroll">
          <table className="asset-table airflow-table">
            <thead>
              <tr>
                <th>Airflow Run</th>
                <th>State</th>
                <th>Started</th>
                <th>Pipeline</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {runs.items.length ? runs.items.map((run) => (
                <tr key={run.dag_run_id}>
                  <td><code>{run.dag_run_id}</code><small>{run.run_type || 'manual'}</small></td>
                  <td><StatusPill status={run.state} /></td>
                  <td><strong>{formatDate(run.start_date || run.queued_at)}</strong><small>{run.end_date ? `Ended ${formatDate(run.end_date)}` : 'In progress / queued'}</small></td>
                  <td><strong>{run.conf.pipeline_code || 'FED_FUNDS_RATE_PIPELINE'}</strong><small>Run date {run.conf.run_date || '—'}</small></td>
                  <td><button className="table-action" type="button" onClick={() => inspectRun(run.dag_run_id)}>Inspect</button></td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="5" className="table-empty">
                    {runsLoading ? 'Loading Airflow run history…' : 'No DFF Airflow runs have been recorded yet.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel asset-table-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">SKYCOMMAND → AIRFLOW ASSET EVENT</span>
            <h2>DFF ingestion-complete trigger</h2>
            <p className="rule-copy">
              The latest terminal successful SkyCommand FRED/DFF ingestion run can emit a native
              Airflow asset event. Duplicate signals reuse the existing event instead of creating
              another orchestration run.
            </p>
          </div>
          <button
            className="primary-button"
            type="button"
            onClick={launchIngestionEvent}
            disabled={
              eventLaunching
              || eventLoading
              || !ingestionEvent.eligible
              || !ingestionEvent.asset_registered
            }
          >
            {eventLaunching
              ? 'Emitting…'
              : ingestionEvent.already_emitted
                ? 'Reuse Event Proof'
                : 'Emit Ingestion Event'}
          </button>
        </div>
        {eventMessage ? <div className="workspace-alert">{eventMessage}</div> : null}
        <div className="airflow-event-grid">
          <article>
            <span>SkyCommand Run</span>
            <strong>{ingestionEvent.ingestion_run?.ingestion_run_id || '—'}</strong>
            <small>{ingestionEvent.ingestion_run?.status_code || 'Waiting for evidence'}</small>
          </article>
          <article>
            <span>Source Asset</span>
            <strong>FRED / DFF</strong>
            <small>{ingestionEvent.asset_uri}</small>
          </article>
          <article>
            <span>Airflow Asset</span>
            <strong>{ingestionEvent.asset_registered ? 'REGISTERED' : 'WAITING'}</strong>
            <small>Native REST API v2 asset-event boundary</small>
          </article>
          <article>
            <span>Signal State</span>
            <strong>
              {ingestionEvent.already_emitted
                ? 'EMITTED'
                : ingestionEvent.eligible ? 'READY' : 'WAITING'}
            </strong>
            <small>{ingestionEvent.message}</small>
          </article>
        </div>
        {ingestionEvent.event ? (
          <div className="rule-footer">
            <span>Event #{ingestionEvent.event.id}</span>
            <span>{formatDate(ingestionEvent.event.timestamp)}</span>
            <span>
              {ingestionEvent.event.created_dag_run_ids?.[0] || 'Scheduler processing'}
            </span>
          </div>
        ) : null}
      </section>

      {selectedRun ? (
        <section className="panel asset-table-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">TASK EVIDENCE</span>
              <h2>{selectedRun.run.dag_run_id}</h2>
              <p className="rule-copy">Studio replay key: {selectedRun.studio_run_key || '—'}</p>
            </div>
            <StatusPill status={selectedRun.run.state} />
          </div>
          <div className="rule-footer">
            {Object.entries(selectedRun.task_state_counts).map(([state, count]) => (
              <span key={state}>{state}: {count}</span>
            ))}
          </div>
          <div className="asset-table-scroll">
            <table className="asset-table airflow-table">
              <thead>
                <tr><th>Task</th><th>State</th><th>Try</th><th>Duration</th><th>Operator</th></tr>
              </thead>
              <tbody>
                {selectedRun.tasks.map((task) => (
                  <tr key={`${task.task_id}:${task.map_index}`}>
                    <td><strong>{task.task_display_name}</strong><code>{task.task_id}</code></td>
                    <td><StatusPill status={task.state} /></td>
                    <td><strong>{task.try_number}</strong></td>
                    <td><strong>{task.duration == null ? '—' : `${task.duration.toFixed(2)}s`}</strong></td>
                    <td><strong>{task.operator || 'Task SDK'}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="two-column-grid">
        <article className="panel compact-panel airflow-contract-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">ORCHESTRATION CONTRACT</span>
              <h2>Airflow owns durable batch scheduling</h2>
            </div>
            <span className="phase-badge">5.4</span>
          </div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Isolated runtime</strong><small>Airflow keeps its own metadata PostgreSQL database and service processes.</small></div></li>
            <li><span>02</span><div><strong>Stable API boundary</strong><small>Studio triggers and observes Airflow through authenticated REST API v2 calls only.</small></div></li>
            <li><span>03</span><div><strong>Replay-safe callback</strong><small>Each DAG run calls the proven Studio engine with an Airflow-derived replay key.</small></div></li>
            <li><span>04</span><div><strong>Task evidence</strong><small>DAG-run and task-instance state is projected back into the Studio workbench.</small></div></li>
            <li><span>05</span><div><strong>Asset event trigger</strong><small>SkyCommand ingestion completion becomes a deduplicated Airflow asset event.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel airflow-next-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PHASE 5 CLOSURE</span>
              <h2>Prove event-driven idempotency</h2>
            </div>
            <span className="rule-mark">→</span>
          </div>
          <p className="rule-copy">
            Emit the latest eligible DFF ingestion event, confirm Airflow schedules the DAG without
            a manual launch, then send the same ingestion signal again and prove that the event and
            Studio materialization are reused safely.
          </p>
          <div className="rule-footer"><span>Asset event</span><span>Deduplication</span><span>4/4 evidence</span></div>
        </article>
      </section>
    </div>
  );
}

export default Airflow;
