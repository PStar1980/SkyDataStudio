import { useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson, postJson } from '../services/api.js';

const PROOF_DAG_ID = 'skydata_studio_fed_funds_rate_pipeline';
const PROOF_PIPELINE_CODE = 'FED_FUNDS_RATE_PIPELINE';

const EMPTY_SUMMARY = {
  connection_status: 'UNAVAILABLE',
  dags: [],
};

const EMPTY_BACKFILLS = {
  dag_id: PROOF_DAG_ID,
  total: 0,
  items: [],
};

function isoDate(offsetDays = 0) {
  const value = new Date();
  value.setDate(value.getDate() + offsetDays);
  return value.toISOString().slice(0, 10);
}

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function backfillStatus(backfill) {
  if (backfill.completed_at) return 'COMPLETED';
  if (backfill.is_paused) return 'PAUSED';
  return 'RUNNING';
}

function SchedulesBackfills() {
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [backfills, setBackfills] = useState(EMPTY_BACKFILLS);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [form, setForm] = useState({
    from_date: isoDate(-1),
    to_date: isoDate(-1),
    reprocess_behavior: 'none',
    max_active_runs: '1',
    run_backwards: false,
  });

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getJson('/api/v1/integrations/airflow/summary', { signal: controller.signal }),
      getJson(`/api/v1/integrations/airflow/dags/${PROOF_DAG_ID}/backfills?limit=20`, {
        signal: controller.signal,
      }),
    ])
      .then(([summaryPayload, backfillPayload]) => {
        setSummary(summaryPayload);
        setBackfills(backfillPayload);
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setMessage(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [refreshKey]);

  const proofDag = useMemo(
    () => summary.dags.find((dag) => dag.dag_id === PROOF_DAG_ID),
    [summary.dags],
  );

  const completedBackfills = useMemo(
    () => backfills.items.filter((item) => item.completed_at).length,
    [backfills.items],
  );

  function updateField(event) {
    const { name, type, checked, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
    }));
  }

  function refresh() {
    setLoading(true);
    setMessage('');
    setRefreshKey((current) => current + 1);
  }

  function createBackfill(event) {
    event.preventDefault();
    setCreating(true);
    setMessage('');
    postJson(`/api/v1/integrations/airflow/dags/${PROOF_DAG_ID}/backfills`, {
      pipeline_code: PROOF_PIPELINE_CODE,
      from_date: form.from_date,
      to_date: form.to_date,
      reprocess_behavior: form.reprocess_behavior,
      max_active_runs: Number(form.max_active_runs),
      run_backwards: form.run_backwards,
    })
      .then((payload) => {
        setMessage(`Backfill ${payload.backfill.id} was created for the controlled proof window.`);
        setLoading(true);
        setRefreshKey((current) => current + 1);
      })
      .catch((error) => setMessage(error.message))
      .finally(() => setCreating(false));
  }

  return (
    <div className="page-stack">
      <section className="page-intro airflow-page-intro">
        <div>
          <span className="eyebrow">PHASE 5.3 · SCHEDULES + CONTROLLED BACKFILLS</span>
          <h1>Schedules &amp; Backfills</h1>
          <p>
            Prove time-based Airflow orchestration with a version-controlled daily schedule and bounded
            replay windows. Backfill runs still execute through the same Studio replay, mapping,
            validation, and materialization contract.
          </p>
        </div>
        <div className="page-intro-actions">
          <button className="primary-button" type="button" onClick={refresh} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh Controls'}
          </button>
        </div>
      </section>

      {message ? <div className="workspace-alert">{message}</div> : null}

      <section className="airflow-metric-grid schedule-metric-grid">
        <article className="metric-card">
          <span>Airflow</span>
          <strong>{summary.connection_status}</strong>
          <small>REST API v2 boundary</small>
        </article>
        <article className="metric-card">
          <span>DFF Schedule</span>
          <strong>{proofDag?.timetable || 'WAITING'}</strong>
          <small>Version-controlled DAG timetable</small>
        </article>
        <article className="metric-card">
          <span>DAG State</span>
          <strong>{proofDag ? (proofDag.paused ? 'PAUSED' : 'ACTIVE') : 'WAITING'}</strong>
          <small>Scheduler eligibility</small>
        </article>
        <article className="metric-card">
          <span>Backfills</span>
          <strong>{backfills.total}</strong>
          <small>{completedBackfills} completed</small>
        </article>
        <article className="metric-card">
          <span>Guardrail</span>
          <strong>7 DAYS</strong>
          <small>Maximum local proof window</small>
        </article>
      </section>

      <section className="two-column-grid schedule-control-grid">
        <article className="panel compact-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">SCHEDULE CONTRACT</span>
              <h2>Daily DFF orchestration</h2>
            </div>
            <StatusPill status={proofDag?.paused ? 'PAUSED' : proofDag ? 'ACTIVE' : 'WAITING'} />
          </div>
          <div className="schedule-contract-list">
            <div><span>DAG</span><strong>{PROOF_DAG_ID}</strong></div>
            <div><span>Pipeline</span><strong>{PROOF_PIPELINE_CODE}</strong></div>
            <div><span>Timetable</span><strong>{proofDag?.timetable || 'Airflow has not parsed the schedule yet.'}</strong></div>
            <div><span>Catchup</span><strong>Disabled for normal scheduler runs</strong></div>
            <div><span>Concurrency</span><strong>1 active DAG run</strong></div>
          </div>
          <p className="rule-copy">
            Scheduled and backfill runs derive their Studio RUN_DATE from the Airflow data interval.
            Manual launches can still provide an explicit run date.
          </p>
        </article>

        <article className="panel compact-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">CONTROLLED BACKFILL</span>
              <h2>Create a bounded replay window</h2>
            </div>
            <span className="phase-badge">5.3</span>
          </div>
          <form className="backfill-form" onSubmit={createBackfill}>
            <label>
              <span>From date</span>
              <input type="date" name="from_date" value={form.from_date} onChange={updateField} required />
            </label>
            <label>
              <span>To date</span>
              <input type="date" name="to_date" value={form.to_date} onChange={updateField} required />
            </label>
            <label>
              <span>Reprocess behavior</span>
              <select name="reprocess_behavior" value={form.reprocess_behavior} onChange={updateField}>
                <option value="none">Missing runs only</option>
                <option value="failed">Missing + failed runs</option>
                <option value="completed">All completed/failed runs</option>
              </select>
            </label>
            <label>
              <span>Max active runs</span>
              <select name="max_active_runs" value={form.max_active_runs} onChange={updateField}>
                <option value="1">1 — safest proof</option>
                <option value="2">2</option>
                <option value="3">3</option>
              </select>
            </label>
            <label className="backfill-checkbox">
              <input type="checkbox" name="run_backwards" checked={form.run_backwards} onChange={updateField} />
              <span>Run newest interval first</span>
            </label>
            <div className="backfill-warning">
              Keep the proof window small. The DFF pipeline currently materializes the full governed source
              set on each run; Phase 5.3 is proving orchestration semantics, not incremental partition pruning.
            </div>
            <button
              className="primary-button"
              type="submit"
              disabled={creating || proofDag?.paused || !proofDag}
            >
              {creating ? 'Creating…' : 'Create Backfill'}
            </button>
          </form>
        </article>
      </section>

      <section className="panel asset-table-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">BACKFILL HISTORY</span>
            <h2>Airflow replay-window evidence</h2>
          </div>
          <span className="panel-meta">{backfills.total} backfills</span>
        </div>
        <div className="asset-table-scroll">
          <table className="asset-table airflow-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Window</th>
                <th>Policy</th>
                <th>Concurrency</th>
                <th>State</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {backfills.items.length ? backfills.items.map((backfill) => (
                <tr key={backfill.id}>
                  <td><strong>#{backfill.id}</strong><code>{backfill.dag_id}</code></td>
                  <td><strong>{new Date(backfill.from_date).toLocaleDateString()} → {new Date(backfill.to_date).toLocaleDateString()}</strong></td>
                  <td><strong>{backfill.reprocess_behavior.toUpperCase()}</strong><small>{backfill.run_backwards ? 'Newest first' : 'Oldest first'}</small></td>
                  <td><strong>{backfill.max_active_runs}</strong><small>max active runs</small></td>
                  <td><StatusPill status={backfillStatus(backfill)} /></td>
                  <td><strong>{formatDate(backfill.created_at)}</strong><small>{backfill.completed_at ? `Completed ${formatDate(backfill.completed_at)}` : 'In progress'}</small></td>
                </tr>
              )) : (
                <tr><td colSpan="6" className="table-empty">No controlled Airflow backfills have been created yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="two-column-grid">
        <article className="panel compact-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">PHASE 5.3 RULES</span><h2>Backfill safety contract</h2></div>
            <span className="rule-mark">✓</span>
          </div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Time-based DAG</strong><small>Backfills use the same daily timetable that drives normal scheduled execution.</small></div></li>
            <li><span>02</span><div><strong>Bounded windows</strong><small>Studio limits the local proof to seven calendar days and three concurrent runs.</small></div></li>
            <li><span>03</span><div><strong>Safe default</strong><small>Missing-runs-only reprocessing avoids recreating completed logical dates by default.</small></div></li>
            <li><span>04</span><div><strong>Same execution contract</strong><small>Every Airflow run still calls the replay-safe Studio pipeline API rather than bypassing it.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel airflow-next-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">NEXT PROOF</span><h2>Ingestion-complete event trigger</h2></div>
            <span className="rule-mark">→</span>
          </div>
          <p className="rule-copy">
            After the daily schedule and bounded backfill path are proven, the final Phase 5 slice will
            launch the batch from an ingestion-complete signal without coupling Airflow to SkyCommand&apos;s
            internal database.
          </p>
          <div className="rule-footer"><span>Event trigger</span><span>Replay key</span><span>Evidence</span></div>
        </article>
      </section>
    </div>
  );
}

export default SchedulesBackfills;
