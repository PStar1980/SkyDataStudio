import { useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { buildQuery, getJson, postJson } from '../services/api.js';

const EMPTY_SUMMARY = {
  runs: 0,
  step_runs: 0,
  replayed_runs: 0,
  statuses: {},
  environments: {},
};

const RUN_STATUSES = ['SUCCEEDED', 'FAILED', 'RUNNING', 'PENDING'];

function statusTone(status) {
  if (status === 'SUCCEEDED') return 'READY';
  if (status === 'FAILED') return 'BLOCKED';
  return 'PLANNED';
}

function formatTime(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function PipelineRuns() {
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [runs, setRuns] = useState({ total: 0, items: [] });
  const [filters, setFilters] = useState({ search: '', status: '', environment: '' });
  const [selectedRun, setSelectedRun] = useState(null);
  const [detailState, setDetailState] = useState('IDLE');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  const runQuery = useMemo(
    () => buildQuery({ ...filters, limit: 250 }),
    [filters],
  );

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getJson('/api/v1/pipeline-runs/summary', { signal: controller.signal }),
      getJson(`/api/v1/pipeline-runs${runQuery}`, { signal: controller.signal }),
    ])
      .then(([summaryPayload, runPayload]) => {
        setSummary(summaryPayload);
        setRuns(runPayload);
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      });
    return () => controller.abort();
  }, [runQuery, refreshKey]);

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  async function inspectRun(runId) {
    setDetailState('LOADING');
    setSelectedRun(null);
    setError('');
    try {
      const payload = await getJson(`/api/v1/pipeline-runs/${runId}`);
      setSelectedRun(payload);
      setDetailState('READY');
    } catch (requestError) {
      setError(requestError.message);
      setDetailState('IDLE');
    }
  }

  async function replayRun(mode) {
    if (!selectedRun) return;
    setMessage('');
    setError('');
    try {
      const response = await postJson('/api/v1/pipeline-runs', {
        pipeline_id: selectedRun.pipeline_id,
        version_number: selectedRun.version_number,
        parameters: selectedRun.parameters,
        replay_mode: mode,
      });
      setMessage(response.reused
        ? `${response.run.pipeline_code} reused the existing replay-safe run.`
        : `${response.run.pipeline_code} completed a new materialization run.`);
      setSelectedRun(response.run);
      setRefreshKey((value) => value + 1);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <div className="workspace-page pipeline-runs-page">
      <section className="registry-intro">
        <div>
          <span className="eyebrow">PHASE 4.3 · CURATED TABLE MATERIALIZATION</span>
          <h1>Pipeline Runs</h1>
          <p>
            Read governed SkyCommand observations, apply registered source-to-target mappings, materialize
            curated targets with replay-safe MERGE semantics, and persist row-level execution evidence.
          </p>
        </div>
        <div className="registry-actions">
          <button className="primary-button" type="button" onClick={() => setRefreshKey((value) => value + 1)}>
            Refresh Runs
          </button>
        </div>
      </section>

      {message ? <div className="workspace-banner success-banner">{message}</div> : null}
      {error ? <div className="workspace-banner error-banner">{error}</div> : null}

      <section className="pipeline-run-metric-grid">
        <article className="metric-card"><span>RUNS</span><strong>{summary.runs}</strong><small>Durable local execution records</small></article>
        <article className="metric-card"><span>SUCCEEDED</span><strong>{summary.statuses.SUCCEEDED || 0}</strong><small>Dependency graphs completed</small></article>
        <article className="metric-card"><span>FAILED</span><strong>{summary.statuses.FAILED || 0}</strong><small>Runs requiring attention</small></article>
        <article className="metric-card"><span>REPLAYED</span><strong>{summary.replayed_runs}</strong><small>Idempotent run keys reused</small></article>
        <article className="metric-card"><span>STEP RESULTS</span><strong>{summary.step_runs}</strong><small>Structured execution evidence</small></article>
      </section>

      <section className="panel pipeline-run-inventory">
        <div className="panel-heading">
          <div><span className="eyebrow">RUN HISTORY</span><h2>Local pipeline execution evidence</h2></div>
          <span className="panel-meta">{runs.total} runs</span>
        </div>
        <div className="pipeline-filter-grid">
          <label><span>Search</span><input name="search" value={filters.search} onChange={updateFilter} placeholder="Pipeline, run key..." /></label>
          <label><span>Status</span><select name="status" value={filters.status} onChange={updateFilter}><option value="">All statuses</option>{RUN_STATUSES.map((value) => <option key={value}>{value}</option>)}</select></label>
          <label><span>Environment</span><select name="environment" value={filters.environment} onChange={updateFilter}><option value="">All environments</option>{Object.keys(summary.environments).map((value) => <option key={value}>{value}</option>)}</select></label>
        </div>
        <div className="asset-table-scroll">
          <table className="asset-table pipeline-run-table">
            <thead><tr><th>Run</th><th>Pipeline</th><th>Version</th><th>Status</th><th>Steps</th><th>Replay</th><th>Started</th><th /></tr></thead>
            <tbody>
              {runs.items.map((run) => (
                <tr key={run.id}>
                  <td><div className="asset-primary"><strong>{run.run_key}</strong><small>{run.execution_mode} · {run.environment}</small></div></td>
                  <td><div className="asset-primary"><strong>{run.pipeline_name}</strong><code>{run.pipeline_code}</code></div></td>
                  <td><strong>v{run.version_number}</strong><small>{run.trigger_type}</small></td>
                  <td><StatusPill status={run.status} tone={statusTone(run.status)} /></td>
                  <td><strong>{run.succeeded_steps}/{run.step_count}</strong><small>{run.failed_steps} failed</small></td>
                  <td><strong>{run.replay_count}</strong><small>reuse count</small></td>
                  <td><strong>{formatTime(run.started_at)}</strong><small>{run.completed_at ? 'Completed' : 'In progress'}</small></td>
                  <td><button className="table-action" type="button" onClick={() => inspectRun(run.id)}>Inspect</button></td>
                </tr>
              ))}
              {!runs.items.length ? <tr><td colSpan="8" className="table-empty">No pipeline runs match the current filters.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      {detailState !== 'IDLE' ? (
        <div className="drawer-layer">
          <button className="drawer-scrim" type="button" onClick={() => setDetailState('IDLE')} aria-label="Close run detail" />
          <aside className="asset-detail-drawer pipeline-run-detail-drawer">
            <header className="drawer-header">
              <div><span className="eyebrow">PIPELINE RUN</span><h2>{selectedRun?.pipeline_name || 'Loading run...'}</h2><small>{selectedRun?.run_key}</small></div>
              <button type="button" onClick={() => setDetailState('IDLE')}>×</button>
            </header>
            {detailState === 'LOADING' ? <div className="drawer-loading">Loading structured run evidence...</div> : null}
            {selectedRun ? (
              <div className="drawer-body">
                <section className="pipeline-contract-card">
                  <div><span>STATUS</span><strong>{selectedRun.status}</strong><small>{selectedRun.execution_mode}</small></div>
                  <div><span>VERSION</span><strong>v{selectedRun.version_number}</strong><small>{selectedRun.environment}</small></div>
                  <div><span>REPLAYS</span><strong>{selectedRun.replay_count}</strong><small>same logical run key</small></div>
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Replay contract</h3><StatusPill status={selectedRun.status} tone={statusTone(selectedRun.status)} /></div>
                  <dl className="detail-definition-grid">
                    <div><dt>Started</dt><dd>{formatTime(selectedRun.started_at)}</dd></div>
                    <div><dt>Completed</dt><dd>{formatTime(selectedRun.completed_at)}</dd></div>
                    <div><dt>Succeeded</dt><dd>{selectedRun.succeeded_steps}</dd></div>
                    <div><dt>Failed</dt><dd>{selectedRun.failed_steps}</dd></div>
                  </dl>
                  <div className="run-parameter-strip">
                    {Object.entries(selectedRun.parameters).map(([key, value]) => <span key={key}><code>{key}</code><strong>{String(value)}</strong></span>)}
                    {!Object.keys(selectedRun.parameters).length ? <small>No runtime parameters resolved.</small> : null}
                  </div>
                  <div className="run-replay-actions">
                    <button className="secondary-button" type="button" onClick={() => replayRun('REUSE')}>Replay Safely</button>
                    <button className="primary-button" type="button" onClick={() => replayRun('FORCE_NEW')}>Force New Materialization Run</button>
                  </div>
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading">
                    <h3>Materialization evidence</h3>
                    <span>{selectedRun.result.target_relation || 'Target pending'}</span>
                  </div>
                  <div className="materialization-evidence-grid">
                    <div><span>ROWS READ</span><strong>{selectedRun.result.rows_read ?? 0}</strong></div>
                    <div><span>INSERTED</span><strong>{selectedRun.result.rows_inserted ?? 0}</strong></div>
                    <div><span>UPDATED</span><strong>{selectedRun.result.rows_updated ?? 0}</strong></div>
                    <div><span>UNCHANGED</span><strong>{selectedRun.result.rows_unchanged ?? 0}</strong></div>
                    <div><span>REJECTED</span><strong>{selectedRun.result.rows_rejected ?? 0}</strong></div>
                    <div><span>PUBLISHED</span><strong>{selectedRun.result.rows_published ?? 0}</strong></div>
                    <div><span>TARGET ROWS</span><strong>{selectedRun.result.target_row_count ?? '—'}</strong></div>
                    <div>
                      <span>MATERIALIZER</span>
                      <strong>{selectedRun.result.materialization_executed ? 'EXECUTED' : 'NOT EXECUTED'}</strong>
                    </div>
                    <div>
                      <span>ROWS CHANGED</span>
                      <strong>{selectedRun.result.rows_changed ?? 0}</strong>
                    </div>
                  </div>
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Structured step results</h3><span>{selectedRun.step_runs.length}</span></div>
                  <div className="pipeline-run-step-list">
                    {selectedRun.step_runs.map((step) => (
                      <article key={step.id}>
                        <div className="pipeline-step-index">{String(step.execution_order).padStart(2, '0')}</div>
                        <div className="pipeline-step-copy">
                          <div><code>{step.step_code}</code><StatusPill status={step.status} tone={statusTone(step.status)} /></div>
                          <strong>{step.step_name}</strong>
                          <small>{step.step_type} · attempts {step.attempt_count} · {step.duration_ms ?? 0} ms</small>
                          <p>{step.result.summary || step.error_message || 'Structured result captured.'}</p>
                          <div className="run-result-tags">
                            {step.result.operation ? <span>{step.result.operation}</span> : null}
                            {step.result.validation_status ? <span>{step.result.validation_status}</span> : null}
                            {step.result.publication_status ? <span>{step.result.publication_status}</span> : null}
                            {step.result.rows_read != null ? <span>{step.result.rows_read} READ</span> : null}
                            {step.result.rows_inserted != null ? <span>{step.result.rows_inserted} INSERTED</span> : null}
                            {step.result.rows_updated != null ? <span>{step.result.rows_updated} UPDATED</span> : null}
                            {step.result.rows_unchanged != null ? <span>{step.result.rows_unchanged} UNCHANGED</span> : null}
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Run result</h3><span>{selectedRun.result.result_version}</span></div>
                  <pre className="run-result-json">{JSON.stringify(selectedRun.result, null, 2)}</pre>
                </section>
              </div>
            ) : null}
          </aside>
        </div>
      ) : null}
    </div>
  );
}

export default PipelineRuns;
