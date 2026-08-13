import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from './StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY = {
  artifact_status: 'MISSING',
  evidence_trust_posture: 'PENDING',
  contract_status: 'PENDING',
  check_count: 0,
  passed_check_count: 0,
  required_contract_rule_count: 0,
  satisfied_contract_rule_count: 0,
  active_incident_count: 0,
  blocking_incident_count: 0,
  protected_asset_count: 0,
  protected_field_count: 0,
  overlays: [],
};

function tone(status) {
  if (status === 'TRUSTED' || status === 'COMPLIANT' || status === 'READY') return 'READY';
  if (status === 'DEGRADED' || status === 'PARTIAL') return 'WARNING';
  if (status === 'BLOCKED') return 'BLOCKED';
  return 'PLANNED';
}

function LineageTrustPanel() {
  const [summary, setSummary] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await getJson('/api/v1/lineage/trust/summary'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/lineage/trust/summary', { signal: controller.signal })
      .then(setSummary)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const assets = useMemo(
    () => summary.overlays.filter((overlay) => overlay.scope === 'ASSET'),
    [summary.overlays],
  );
  const fields = useMemo(
    () => summary.overlays.filter((overlay) => overlay.scope === 'FIELD'),
    [summary.overlays],
  );

  return (
    <section className="panel lineage-trust-panel">
      <div className="panel-heading lineage-trust-heading">
        <div>
          <span className="eyebrow">PHASE 8.3 · QUALITY + INCIDENT OVERLAY</span>
          <h2>Trust evidence follows the lineage graph</h2>
          <p>
            Project dbt checks, source-controlled contract rules, and durable incident state onto the
            assets and fields they protect without moving ownership out of their existing systems.
          </p>
        </div>
        <div className="lineage-trust-actions">
          <StatusPill status={summary.evidence_trust_posture} tone={tone(summary.evidence_trust_posture)} />
          <button className="secondary-button" type="button" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh Trust'}
          </button>
        </div>
      </div>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <div className="lineage-trust-metrics">
        <div><span>CONTRACT</span><strong>{summary.contract_status}</strong><small>{summary.satisfied_contract_rule_count}/{summary.required_contract_rule_count} rules satisfied</small></div>
        <div><span>QUALITY CHECKS</span><strong>{summary.passed_check_count}/{summary.check_count}</strong><small>latest dbt evidence passing</small></div>
        <div><span>PROTECTED ASSETS</span><strong>{summary.protected_asset_count}</strong><small>source + model nodes</small></div>
        <div><span>PROTECTED FIELDS</span><strong>{summary.protected_field_count}</strong><small>column-level trust seams</small></div>
        <div><span>ACTIVE INCIDENTS</span><strong>{summary.active_incident_count}</strong><small>{summary.blocking_incident_count} blocking</small></div>
      </div>

      <div className="lineage-trust-grid">
        <article className="lineage-trust-group">
          <header><div><span className="eyebrow">ASSET TRUST</span><strong>dbt sources and models</strong></div><span>{assets.length} protected</span></header>
          <div className="lineage-trust-list">
            {assets.map((overlay) => (
              <div className="lineage-trust-row" key={overlay.node_id}>
                <div><span>{overlay.layer}</span><strong>{overlay.node_label}</strong><small>{overlay.quality_dimensions.join(' · ') || 'No dimensions'}</small></div>
                <div className="lineage-trust-row-meta">
                  <StatusPill status={overlay.quality_status} tone={tone(overlay.quality_status)} />
                  <small>{overlay.passed_check_count}/{overlay.check_count} checks · {overlay.satisfied_contract_rule_count}/{overlay.contract_rule_count} rules</small>
                  <small>{overlay.active_incident_count} active incident{overlay.active_incident_count === 1 ? '' : 's'}</small>
                </div>
              </div>
            ))}
            {!assets.length ? <p>No asset-level trust evidence is mapped yet.</p> : null}
          </div>
        </article>

        <article className="lineage-trust-group">
          <header><div><span className="eyebrow">FIELD TRUST</span><strong>quality-protected columns</strong></div><span>{fields.length} protected</span></header>
          <div className="lineage-trust-list lineage-trust-field-list">
            {fields.map((overlay) => (
              <div className="lineage-trust-row" key={overlay.node_id}>
                <div><span>{overlay.layer}</span><strong>{overlay.node_label}</strong><small>{overlay.quality_dimensions.join(' · ') || 'No dimensions'}</small></div>
                <div className="lineage-trust-row-meta">
                  <StatusPill status={overlay.quality_status} tone={tone(overlay.quality_status)} />
                  <small>{overlay.passed_check_count}/{overlay.check_count} checks · {overlay.satisfied_contract_rule_count}/{overlay.contract_rule_count} rules</small>
                </div>
              </div>
            ))}
            {!fields.length ? <p>No field-level trust evidence is mapped yet.</p> : null}
          </div>
        </article>
      </div>
    </section>
  );
}

export default LineageTrustPanel;
