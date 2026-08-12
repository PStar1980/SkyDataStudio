import { useCallback, useEffect, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson, postJson } from '../services/api.js';

const EMPTY = {
  contract_code: 'FED_FUNDS_RATE_DAILY_QUALITY',
  contract_version: '1.1.0',
  current_contract_status: 'PENDING',
  reliability_status: 'PENDING',
  window_days: 30,
  minimum_compliance_rate: 0.99,
  observed_compliance_rate: 0,
  observation_count: 0,
  compliant_count: 0,
  degraded_count: 0,
  blocked_count: 0,
  pending_count: 0,
  current_compliant_streak: 0,
  window_start: null,
  window_end: null,
  observations: [],
};

function toneForStatus(status) {
  if (['MEETING', 'COMPLIANT'].includes(status)) return 'READY';
  if (['AT_RISK', 'DEGRADED', 'PENDING'].includes(status)) return 'WARNING';
  if (['BREACHED', 'BLOCKED'].includes(status)) return 'BLOCKED';
  return 'UNKNOWN';
}

function percent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function dateLabel(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function QualityReliability() {
  const [summary, setSummary] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [capturing, setCapturing] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await getJson('/api/v1/quality/reliability/summary'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/quality/reliability/summary', { signal: controller.signal })
      .then(setSummary)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function capture() {
    setCapturing(true);
    setError('');
    setMessage('');
    try {
      const result = await postJson('/api/v1/quality/reliability/capture');
      setSummary(result.summary);
      setMessage(
        result.observation_created
          ? 'Captured one new reliability observation from the latest dbt invocation.'
          : 'Latest dbt invocation was already captured; reliability history was left unchanged.',
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setCapturing(false);
    }
  }

  return (
    <div className="page-stack reliability-page">
      <section className="workspace-intro reliability-intro">
        <div>
          <span className="eyebrow">PHASE 7.4 · QUALITY SLO + RELIABILITY HISTORY</span>
          <h1>Quality Reliability</h1>
          <p>
            Turn contract evaluations into idempotent historical observations, then measure whether
            consumer-ready data is meeting its source-controlled reliability objective over time.
          </p>
        </div>
        <div className="incident-actions-row">
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh History'}
          </button>
          <button className="primary-button" type="button" onClick={capture} disabled={capturing}>
            {capturing ? 'Capturing…' : 'Capture Latest Evidence'}
          </button>
        </div>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}
      {message ? <div className="incident-reconcile-note">{message}</div> : null}

      <section className="metric-grid reliability-metric-grid">
        <article className="metric-card"><span>SLO Posture</span><strong>{summary.reliability_status}</strong><small>{summary.contract_code}</small></article>
        <article className="metric-card"><span>Window Compliance</span><strong>{percent(summary.observed_compliance_rate)}</strong><small>Target {percent(summary.minimum_compliance_rate)}</small></article>
        <article className="metric-card"><span>Observations</span><strong>{summary.observation_count}</strong><small>{summary.window_days}-day rolling window</small></article>
        <article className="metric-card"><span>Blocking</span><strong>{summary.blocked_count}</strong><small>{summary.degraded_count} degraded · {summary.pending_count} pending</small></article>
        <article className="metric-card"><span>Clean Streak</span><strong>{summary.current_compliant_streak}</strong><small>Consecutive compliant observations</small></article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">RELIABILITY OBJECTIVE</span><h2>Consumer readiness measured from durable evidence</h2></div>
          <StatusPill status={summary.reliability_status} tone={toneForStatus(summary.reliability_status)} />
        </div>
        <div className="reliability-objective-grid">
          <article><span>Contract Version</span><strong>{summary.contract_version}</strong><small>Policy changes remain source-controlled</small></article>
          <article><span>Current Gate</span><strong>{summary.current_contract_status}</strong><small>Latest quality contract state</small></article>
          <article><span>Window</span><strong>{summary.window_days} days</strong><small>{dateLabel(summary.window_start)} → {dateLabel(summary.window_end)}</small></article>
          <article><span>Target</span><strong>{percent(summary.minimum_compliance_rate)}</strong><small>Minimum compliant observation rate</small></article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">OBSERVATION HISTORY</span><h2>One row per dbt evidence invocation</h2></div>
          <span className="panel-meta">{summary.observation_count} observations</span>
        </div>
        <div className="table-shell">
          <table className="reliability-table">
            <thead>
              <tr><th>Captured</th><th>Invocation</th><th>Contract</th><th>Trust</th><th>Pass Rate</th><th>Active Incidents</th><th>Blocking</th></tr>
            </thead>
            <tbody>
              {summary.observations.slice().reverse().map((observation) => (
                <tr key={observation.id}>
                  <td>{dateLabel(observation.captured_at)}</td>
                  <td><code>{observation.evidence_invocation_id || 'No invocation id'}</code><small>{dateLabel(observation.evidence_generated_at)}</small></td>
                  <td><StatusPill status={observation.contract_status} tone={toneForStatus(observation.contract_status)} /></td>
                  <td>{observation.evidence_trust_posture}</td>
                  <td>{percent(observation.pass_rate)}</td>
                  <td>{observation.active_incident_count}</td>
                  <td>{observation.blocking_active_incident_count}</td>
                </tr>
              ))}
              {!summary.observations.length ? (
                <tr>
                  <td className="incident-empty" colSpan="7">
                    <strong>No reliability observations yet.</strong>
                    <small>Capture the latest evidence once; repeated capture of the same dbt invocation is intentionally idempotent.</small>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="two-column-grid">
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">ACCEPTANCE CONTRACT</span><h2>What Phase 7.4 proves</h2></div><span className="phase-badge">7.4</span></div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>SLO policy is versioned</strong><small>The Federal Funds Rate quality contract owns a 30-day, 99% readiness objective.</small></div></li>
            <li><span>02</span><div><strong>History is idempotent</strong><small>A dbt invocation contributes at most one observation even when reconciliation is repeated.</small></div></li>
            <li><span>03</span><div><strong>Reliability is evidence-backed</strong><small>Window compliance, streaks, trust posture, and incident counts come from durable observations rather than invented uptime.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">BOUNDARY</span><h2>Observed reliability, not synthetic uptime</h2></div><span className="rule-mark">◷</span></div>
          <p className="rule-copy">
            Phase 7.4 measures captured quality-evidence observations. It does not pretend irregular local development captures are continuous service uptime; scheduled capture and notification routing remain later operational integrations.
          </p>
          <div className="rule-footer"><span>Evidence identity</span><span>Idempotent history</span><span>Source-controlled target</span></div>
        </article>
      </section>
    </div>
  );
}

export default QualityReliability;
