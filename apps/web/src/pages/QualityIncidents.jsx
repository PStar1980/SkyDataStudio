import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson, postJson } from '../services/api.js';

const EMPTY = {
  contract_code: 'FED_FUNDS_RATE_DAILY_QUALITY',
  contract_status: 'PENDING',
  artifact_status: 'PENDING',
  total_count: 0,
  active_count: 0,
  open_count: 0,
  acknowledged_count: 0,
  resolved_count: 0,
  blocking_active_count: 0,
  warning_active_count: 0,
  incidents: [],
};

function toneForStatus(status) {
  if (['COMPLIANT', 'RESOLVED'].includes(status)) return 'READY';
  if (['DEGRADED', 'ACKNOWLEDGED', 'PENDING'].includes(status)) return 'WARNING';
  if (['BLOCKED', 'OPEN'].includes(status)) return 'BLOCKED';
  return 'UNKNOWN';
}

function dateLabel(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function titleCase(value) {
  return String(value || '—').toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function QualityIncidents() {
  const [summary, setSummary] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [reconciling, setReconciling] = useState(false);
  const [error, setError] = useState('');
  const [reconcileMessage, setReconcileMessage] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [actor, setActor] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  const selected = useMemo(
    () => summary.incidents.find((incident) => incident.id === selectedId) || null,
    [selectedId, summary.incidents],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await getJson('/api/v1/quality/incidents/summary'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/quality/incidents/summary', { signal: controller.signal })
      .then(setSummary)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function reconcile() {
    setReconciling(true);
    setError('');
    setReconcileMessage('');
    try {
      const result = await postJson('/api/v1/quality/incidents/reconcile');
      setSummary(result.summary);
      setReconcileMessage(
        `${result.created_count} created · ${result.reopened_count} reopened · ${result.resolved_count} auto-resolved`,
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setReconciling(false);
    }
  }

  async function act(action) {
    if (!selected || !actor.trim()) return;
    setSaving(true);
    setError('');
    try {
      await postJson(`/api/v1/quality/incidents/${selected.id}/${action}`, {
        actor: actor.trim(),
        note: note.trim() || null,
      });
      setSelectedId(null);
      setActor('');
      setNote('');
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  const hasIncidents = summary.incidents.length > 0;

  return (
    <div className="page-stack incidents-page">
      <section className="workspace-intro incidents-intro">
        <div>
          <span className="eyebrow">PHASE 7.3 · DURABLE QUALITY INCIDENTS + REMEDIATION LIFECYCLE</span>
          <h1>Quality Incidents</h1>
          <p>
            Reconcile source-controlled quality gates into durable Studio-owned incident records,
            then preserve acknowledgement, ownership, resolution, recurrence, and lifecycle history.
          </p>
        </div>
        <div className="incident-actions-row">
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh Register'}
          </button>
          <button className="primary-button" type="button" onClick={reconcile} disabled={reconciling}>
            {reconciling ? 'Reconciling…' : 'Reconcile Evidence'}
          </button>
        </div>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}
      {reconcileMessage ? <div className="incident-reconcile-note">{reconcileMessage}</div> : null}

      <section className="metric-grid incidents-metric-grid">
        <article className="metric-card"><span>Contract Gate</span><strong>{summary.contract_status}</strong><small>{summary.contract_code}</small></article>
        <article className="metric-card"><span>Active</span><strong>{summary.active_count}</strong><small>{summary.open_count} open · {summary.acknowledged_count} acknowledged</small></article>
        <article className="metric-card"><span>Blocking</span><strong>{summary.blocking_active_count}</strong><small>{summary.warning_active_count} warning incidents</small></article>
        <article className="metric-card"><span>Resolved</span><strong>{summary.resolved_count}</strong><small>Durable historical records retained</small></article>
        <article className="metric-card"><span>Evidence</span><strong>{summary.artifact_status}</strong><small>Latest quality-contract evaluation</small></article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">INCIDENT LIFECYCLE</span><h2>Failure becomes owned operational evidence</h2></div>
          <StatusPill status={summary.contract_status} tone={toneForStatus(summary.contract_status)} />
        </div>
        <div className="incident-lifecycle-grid">
          <article><span>01 · DETECT</span><strong>OPEN</strong><small>BLOCK, MISSING, or WARN contract evidence creates one durable incident per rule.</small></article>
          <article><span>02 · OWN</span><strong>ACKNOWLEDGED</strong><small>An operator accepts responsibility with an identity and optional remediation note.</small></article>
          <article><span>03 · VERIFY</span><strong>RESOLVED</strong><small>Returning PASS evidence auto-resolves; manual resolution remains auditable.</small></article>
          <article><span>04 · RECUR</span><strong>REOPENED</strong><small>A resolved rule that fails again reopens the same incident and increments occurrence history.</small></article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">DURABLE REGISTER</span><h2>Quality incidents and remediation ownership</h2></div>
          <span className="panel-meta">{summary.total_count} historical incidents</span>
        </div>
        <div className="table-shell">
          <table className="incident-table">
            <thead>
              <tr><th>Incident</th><th>Status</th><th>Severity</th><th>Rule</th><th>Evidence</th><th>Owner</th><th>Occurrences</th><th>Last Detected</th><th /></tr>
            </thead>
            <tbody>
              {summary.incidents.map((incident) => (
                <tr key={incident.id}>
                  <td><strong>{incident.target_name}</strong><small>{incident.quality_dimension} · {incident.layer}</small></td>
                  <td><StatusPill status={incident.status} tone={toneForStatus(incident.status)} /></td>
                  <td><span className={`incident-severity severity-${incident.severity.toLowerCase()}`}>{incident.severity}</span></td>
                  <td><strong>{incident.rule_label}</strong><small>{incident.rule_code}</small></td>
                  <td><strong>{incident.evidence_outcome}</strong><small>{incident.matched_status || 'No matched status'}</small></td>
                  <td>{incident.acknowledged_by || '—'}</td>
                  <td>{incident.occurrence_count}</td>
                  <td>{dateLabel(incident.last_detected_at)}</td>
                  <td><button className="table-action" type="button" onClick={() => setSelectedId(incident.id)}>Inspect</button></td>
                </tr>
              ))}
              {!hasIncidents ? (
                <tr>
                  <td className="incident-empty" colSpan="9">
                    <strong>No durable quality incidents.</strong>
                    <small>The current contract is clean; reconciliation will only persist real warning or blocking evidence.</small>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      {selected ? (
        <section className="panel incident-detail-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">INCIDENT DETAIL</span><h2>{selected.rule_label}</h2></div>
            <button className="secondary-button" type="button" onClick={() => setSelectedId(null)}>Close</button>
          </div>
          <div className="incident-detail-grid">
            <article><span>Status</span><strong>{selected.status}</strong><small>{selected.severity}</small></article>
            <article><span>Evidence</span><strong>{selected.evidence_outcome}</strong><small>{selected.matched_check_name || 'No matched dbt check'}</small></article>
            <article><span>First Detected</span><strong>{dateLabel(selected.first_detected_at)}</strong><small>Occurrence {selected.occurrence_count}</small></article>
            <article><span>Last Detected</span><strong>{dateLabel(selected.last_detected_at)}</strong><small>{selected.message}</small></article>
          </div>

          <div className="incident-workflow-grid">
            <div className="incident-action-form">
              <label>
                <span>Operator</span>
                <input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Name or operator identity" />
              </label>
              <label>
                <span>Remediation note</span>
                <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="What is being investigated, changed, or verified?" rows="4" />
              </label>
              <div className="incident-action-buttons">
                {selected.status === 'OPEN' ? (
                  <button className="secondary-button" type="button" disabled={saving || !actor.trim()} onClick={() => act('acknowledge')}>
                    Acknowledge
                  </button>
                ) : null}
                {selected.status !== 'RESOLVED' ? (
                  <button className="primary-button" type="button" disabled={saving || !actor.trim()} onClick={() => act('resolve')}>
                    Resolve
                  </button>
                ) : null}
              </div>
              <small className="incident-form-note">Manual resolution is not a waiver: reconciliation reopens the incident if failing evidence remains.</small>
            </div>

            <div className="incident-history">
              <span className="eyebrow">LIFECYCLE HISTORY</span>
              {selected.events.map((event) => (
                <article key={event.id}>
                  <div><strong>{titleCase(event.event_type)}</strong><small>{dateLabel(event.created_at)}</small></div>
                  <span>{event.actor || 'SYSTEM'}</span>
                  <p>{event.note || 'No note recorded.'}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <section className="two-column-grid incident-proof-grid">
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">ACCEPTANCE CONTRACT</span><h2>What Phase 7.3 proves</h2></div><span className="phase-badge">7.3</span></div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Incidents are earned</strong><small>Studio persists incidents only from real non-passing contract outcomes; a clean contract creates nothing.</small></div></li>
            <li><span>02</span><div><strong>Lifecycle is durable</strong><small>Open, acknowledgement, resolution, and recurrence survive process restarts in Studio PostgreSQL.</small></div></li>
            <li><span>03</span><div><strong>Recovery is evidence-driven</strong><small>PASS evidence closes active incidents automatically, while recurring failures reopen the same durable record.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">BOUNDARY</span><h2>Policy detects; incidents remember</h2></div><span className="rule-mark">↺</span></div>
          <p className="rule-copy">
            dbt still owns test execution and source-controlled contracts still own consumer policy.
            Studio owns only the operational lifecycle created from that evidence: who accepted the issue,
            what happened next, when it cleared, and whether it came back.
          </p>
          <div className="rule-footer"><span>No duplicate test authority</span><span>Persistent history</span><span>Evidence-driven closure</span></div>
        </article>
      </section>
    </div>
  );
}

export default QualityIncidents;
