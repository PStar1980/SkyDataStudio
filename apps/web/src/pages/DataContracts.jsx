import { useCallback, useEffect, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY_QUALITY_CONTRACT = {
  contract_code: 'FED_FUNDS_RATE_DAILY_QUALITY',
  contract_version: '—',
  contract_name: 'Federal Funds Rate Daily Quality Contract',
  description: 'Awaiting source-controlled quality contract evidence.',
  target_name: 'fct_fed_funds_rate_daily',
  layer: 'MART',
  enforcement_mode: 'BLOCK',
  artifact_status: 'MISSING',
  evidence_trust_posture: 'PENDING',
  contract_status: 'PENDING',
  minimum_pass_rate: 1,
  pass_rate: 0,
  required_rule_count: 0,
  satisfied_rule_count: 0,
  warning_rule_count: 0,
  blocking_rule_count: 0,
  missing_rule_count: 0,
  source_path: 'contracts/quality/fed_funds_rate_daily.v1.json',
  rules: [],
};

const EMPTY_COMPATIBILITY = {
  mode: 'PREVIEW',
  status: 'DEGRADED',
  compatible: 0,
  incompatible: 0,
  missing: 0,
  items: [],
};

function tone(status) {
  if (['COMPLIANT', 'COMPATIBLE', 'PASS', 'TRUSTED', 'READY'].includes(status)) return 'READY';
  if (['DEGRADED', 'WARN', 'PENDING'].includes(status)) return 'WARNING';
  if (['BLOCKED', 'BLOCK', 'MISSING', 'INCOMPATIBLE', 'FAIL', 'ERROR'].includes(status)) return 'BLOCKED';
  return 'UNKNOWN';
}

function outcomeLabel(rule) {
  if (rule.outcome === 'PASS') return 'Required evidence satisfied';
  if (rule.outcome === 'WARN') return 'Evidence is warning';
  if (rule.outcome === 'MISSING') return 'Required check is missing';
  if (rule.outcome === 'BLOCK') return 'Latest evidence blocks consumption';
  return 'Waiting for latest dbt evidence';
}

function DataContracts() {
  const [qualityContract, setQualityContract] = useState(EMPTY_QUALITY_CONTRACT);
  const [compatibility, setCompatibility] = useState(EMPTY_COMPATIBILITY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const [qualityPayload, compatibilityPayload] = await Promise.all([
        getJson('/api/v1/quality/contracts/summary', { signal }),
        getJson('/api/v1/integrations/skycommand/contracts/compatibility', { signal }),
      ]);
      setQualityContract(qualityPayload);
      setCompatibility(compatibilityPayload);
    } catch (requestError) {
      if (requestError.name !== 'AbortError') setError(requestError.message);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const compatibilityTotal = compatibility.compatible + compatibility.incompatible + compatibility.missing;

  return (
    <div className="page-stack contracts-page">
      <section className="workspace-intro contracts-intro">
        <div>
          <span className="eyebrow">PHASE 7.2 · QUALITY CONTRACT GATE + CONSUMER COMPATIBILITY</span>
          <h1>Data Contracts</h1>
          <p>
            Keep the rules that decide whether data is safe to consume in source control, then
            evaluate them against dbt evidence while preserving the existing versioned SkyCommand
            consumer boundary.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={() => load()} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh Contracts'}
        </button>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <section className="metric-grid contracts-metric-grid">
        <article className="metric-card"><span>Quality Gate</span><strong>{qualityContract.contract_status}</strong><small>{qualityContract.satisfied_rule_count}/{qualityContract.required_rule_count} required rules satisfied</small></article>
        <article className="metric-card"><span>Pass Rate</span><strong>{Math.round(qualityContract.pass_rate * 100)}%</strong><small>Minimum {Math.round(qualityContract.minimum_pass_rate * 100)}%</small></article>
        <article className="metric-card"><span>Consumer Contracts</span><strong>{compatibility.compatible}/{compatibilityTotal || 0}</strong><small>{compatibility.mode} compatibility evidence</small></article>
        <article className="metric-card"><span>Blocking Rules</span><strong>{qualityContract.blocking_rule_count}</strong><small>{qualityContract.missing_rule_count} missing · {qualityContract.warning_rule_count} warnings</small></article>
        <article className="metric-card"><span>Evidence</span><strong>{qualityContract.artifact_status}</strong><small>{qualityContract.evidence_trust_posture} dbt posture</small></article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">QUALITY CONTRACT</span><h2>{qualityContract.contract_name}</h2></div>
          <StatusPill status={qualityContract.contract_status} tone={tone(qualityContract.contract_status)} />
        </div>
        <div className="contract-definition-grid">
          <article><span>Contract</span><strong>{qualityContract.contract_code}</strong><small>v{qualityContract.contract_version}</small></article>
          <article><span>Target</span><strong>{qualityContract.target_name}</strong><small>{qualityContract.layer} engineering layer</small></article>
          <article><span>Enforcement</span><strong>{qualityContract.enforcement_mode}</strong><small>100% evidence required for this proof</small></article>
          <article><span>Source</span><strong>{qualityContract.source_path}</strong><small>Versioned with the repository</small></article>
        </div>
        <p className="contract-description">{qualityContract.description}</p>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">REQUIRED EVIDENCE</span><h2>Five rules turn latest dbt tests into a consumer gate</h2></div>
          <span className="panel-meta">{qualityContract.required_rule_count} rules</span>
        </div>
        <div className="contract-rule-grid">
          {qualityContract.rules.map((rule) => (
            <article key={rule.code}>
              <header>
                <div><span>{rule.quality_dimension.replaceAll('_', ' ')}</span><strong>{rule.label}</strong></div>
                <StatusPill status={rule.outcome} tone={tone(rule.outcome)} />
              </header>
              <dl>
                <div><dt>Selector</dt><dd>{rule.test_kind}{rule.column_name ? ` · ${rule.column_name}` : ''}</dd></div>
                <div><dt>Required</dt><dd>{rule.required_status}</dd></div>
                <div><dt>Matched Check</dt><dd>{rule.matched_check_name || '—'}</dd></div>
                <div><dt>Latest Result</dt><dd>{rule.matched_status || '—'}{rule.matched_severity ? ` · ${rule.matched_severity}` : ''}</dd></div>
              </dl>
              <p>{outcomeLabel(rule)}</p>
            </article>
          ))}
          {!qualityContract.rules.length ? <div className="quality-empty">No quality contract rules are available yet.</div> : null}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><span className="eyebrow">SKYCOMMAND CONSUMER BOUNDARY</span><h2>Versioned read-only contracts remain compatible</h2></div>
          <StatusPill status={compatibility.status} tone={tone(compatibility.status)} />
        </div>
        <div className="consumer-contract-grid">
          {compatibility.items.map((item) => (
            <article key={item.code}>
              <header><strong>{item.code}</strong><StatusPill status={item.status} tone={tone(item.status)} /></header>
              <span>Expected {item.expected_version}</span>
              <small>Observed {item.observed_version || '—'}</small>
              <p>{item.message}</p>
            </article>
          ))}
          {!compatibility.items.length ? <div className="quality-empty">Consumer compatibility evidence is unavailable.</div> : null}
        </div>
      </section>

      <section className="two-column-grid quality-proof-grid">
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">ACCEPTANCE CONTRACT</span><h2>What Phase 7.2 proves</h2></div><span className="phase-badge">7.2</span></div>
          <ol className="implementation-list">
            <li><span>01</span><div><strong>Policy is source-controlled</strong><small>The consumer gate is versioned independently from dbt-generated test identifiers.</small></div></li>
            <li><span>02</span><div><strong>Evidence decides readiness</strong><small>Required selectors must resolve to passing latest-run dbt checks before the mart is compliant.</small></div></li>
            <li><span>03</span><div><strong>Boundaries stay visible</strong><small>SkyCommand consumer compatibility and Studio quality policy share one contract workbench without sharing ownership.</small></div></li>
          </ol>
        </article>
        <article className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">BOUNDARY</span><h2>Gate now; incidents next</h2></div><span className="rule-mark">▤</span></div>
          <p className="rule-copy">
            Phase 7.2 evaluates policy but does not persist incident lifecycle. Durable incidents,
            acknowledgement, remediation ownership, and historical SLO evidence remain later slices.
          </p>
          <div className="rule-footer"><span>Code as contract</span><span>Artifact evidence</span><span>No duplicated dbt authority</span></div>
        </article>
      </section>
    </div>
  );
}

export default DataContracts;
