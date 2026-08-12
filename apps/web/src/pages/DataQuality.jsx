import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY = {
  artifact_status: 'MISSING',
  trust_posture: 'PENDING',
  generated_at: null,
  dbt_version: null,
  invocation_id: null,
  invocation_command: null,
  elapsed_time_ms: null,
  test_count: 0,
  passed_count: 0,
  warning_count: 0,
  failed_count: 0,
  error_count: 0,
  skipped_count: 0,
  unknown_count: 0,
  source_test_count: 0,
  model_test_count: 0,
  checks: [],
};

function generatedLabel(value) {
  if (!value) return 'Awaiting dbt test evidence';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function titleCase(value) {
  return String(value || '—').toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function toneForStatus(status) {
  if (status === 'PASS' || status === 'TRUSTED') return 'READY';
  if (status === 'WARN' || status === 'DEGRADED' || status === 'PENDING' || status === 'SKIP') return 'WARNING';
  if (status === 'FAIL' || status === 'ERROR' || status === 'BLOCKED') return 'BLOCKED';
  return 'UNKNOWN';
}

function DataQuality() {
  const [summary, setSummary] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dimension, setDimension] = useState('ALL');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await getJson('/api/v1/quality/dbt/summary'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/quality/dbt/summary', { signal: controller.signal })
      .then(setSummary)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const dimensions = useMemo(
    () => ['ALL', ...new Set(summary.checks.map((check) => check.quality_dimension))],
    [summary.checks],
  );
  const filteredChecks = dimension === 'ALL'
    ? summary.checks
    : summary.checks.filter((check) => check.quality_dimension === dimension);

  const layerCoverage = useMemo(() => {
    const layers = ['SOURCE', 'STAGING', 'INTERMEDIATE', 'MART'];
    return layers.map((layer) => {
      const checks = summary.checks.filter((check) => check.layer === layer);
      return {
        layer,
        total: checks.length,
        passed: checks.filter((check) => check.status === 'PASS').length,
      };
    });
  }, [summary.checks]);

  return (
    <div className="page-stack quality-page">
      <section className="workspace-intro quality-intro">
        <div>
          <span className="eyebrow">PHASE 7.1 · DBT QUALITY EVIDENCE + TRUST POSTURE</span>
          <h1>Data Quality</h1>
          <p>
            Turn dbt test artifacts into a readable trust surface: what was checked, where it ran,
            which quality dimension it protects, and whether the latest build is safe to consume.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={load} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh Evidence'}
        </button>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <section className="metric-grid quality-metric-grid">
        <article className="metric-card"><span>Trust Posture</span><strong>{summary.trust_posture}</strong><small>{generatedLabel(summary.generated_at)}</small></article>
        <article className="metric-card"><span>Checks</span><strong>{summary.test_count}</strong><small>{summary.source_test_count} source · {summary.model_test_count} model</small></article>
        <article className="metric-card"><span>Passed</span><strong>{summary.passed_count}</strong><small>Latest dbt build evidence</small></article>
        <article className="metric-card"><span>Blocking</span><strong>{summary.failed_count + summary.error_count}</strong><small>{summary.warning_count} warnings · {summary.skipped_count} skipped</small></article>
        <article className="metric-card"><span>dbt Core</span><strong>{summary.dbt_version || '—'}</strong><small>{summary.elapsed_time_ms == null ? 'Runtime evidence pending' : `${summary.elapsed_time_ms.toFixed(0)} ms build`}</small></article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">QUALITY COVERAGE</span><h2>Trust by engineering layer</h2></div>
          <StatusPill status={summary.trust_posture} tone={toneForStatus(summary.trust_posture)} />
        </div>
        <div className="quality-layer-grid">
          {layerCoverage.map((item) => (
            <article key={item.layer}>
              <span>{item.layer}</span>
              <strong>{item.passed}/{item.total}</strong>
              <small>{item.total ? 'latest checks passing' : 'no checks declared'}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading quality-table-heading">
          <div><span className="eyebrow">TEST INVENTORY</span><h2>Artifact-backed dbt quality checks</h2></div>
          <div className="quality-filter-row">
            {dimensions.map((item) => (
              <button
                className={dimension === item ? 'quality-filter active' : 'quality-filter'}
                key={item}
                type="button"
                onClick={() => setDimension(item)}
              >
                {titleCase(item)}
              </button>
            ))}
          </div>
        </div>
        <div className="table-shell">
          <table className="quality-table">
            <thead><tr><th>Check</th><th>Dimension</th><th>Target</th><th>Layer</th><th>Column</th><th>Severity</th><th>Result</th><th>Runtime</th></tr></thead>
            <tbody>
              {filteredChecks.map((check) => (
                <tr key={check.unique_id}>
                  <td><strong>{check.name}</strong><small>{check.test_kind} · {check.path}</small></td>
                  <td>{titleCase(check.quality_dimension)}</td>
                  <td><strong>{check.target_name}</strong><small>{check.target_resource_type}</small></td>
                  <td><span className="quality-layer-pill">{check.layer}</span></td>
                  <td>{check.column_name || '—'}</td>
                  <td>{check.severity}</td>
                  <td><StatusPill status={check.status} tone={toneForStatus(check.status)} /></td>
                  <td>{check.execution_time_ms == null ? '—' : `${check.execution_time_ms.toFixed(2)} ms`}</td>
                </tr>
              ))}
              {!filteredChecks.length ? <tr><td colSpan="8" className="quality-empty">No quality checks match this view.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="two-column-grid quality-proof-grid">
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">ACCEPTANCE CONTRACT</span><h2>What Phase 7.1 proves</h2></div><span className="phase-badge">7.1</span></div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>One test-evidence seam</strong><small>Manifest definitions and run-results outcomes are joined without duplicating dbt metadata.</small></div></li>
            <li><span>02</span><div><strong>Readable trust posture</strong><small>Pass, warning, failure, error, skip, and unknown states roll into one consumer-facing posture.</small></div></li>
            <li><span>03</span><div><strong>Layer-aware coverage</strong><small>Source, staging, intermediate, and mart checks stay traceable to their owning resource.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">BOUNDARY</span><h2>Evidence first; incidents downstream</h2></div><span className="rule-mark">✓</span></div>
          <p className="rule-copy">
            Phase 7.1 remains the observational evidence seam. Phase 7.2 consumes it as policy,
            and Phase 7.3 now persists operational incidents downstream without changing dbt's
            ownership of test definitions or execution.
          </p>
          <div className="rule-footer"><span>One test authority</span><span>Latest-run evidence</span><span>Downstream incident memory</span></div>
        </article>
      </section>
    </div>
  );
}

export default DataQuality;
