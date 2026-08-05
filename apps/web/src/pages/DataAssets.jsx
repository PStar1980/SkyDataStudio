import { useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { buildQuery, getJson } from '../services/api.js';

const EMPTY_WORKSPACE = {
  mode: 'PREVIEW',
  connection: {
    status: 'UNAVAILABLE',
    message: 'Waiting for the SkyData Studio API.',
    contract_versions: [],
  },
  totals: {
    assets: 0,
    sources: 0,
    current: 0,
    warning: 0,
    error: 0,
    inactive: 0,
    unknown: 0,
    quality_issues: 0,
  },
  filters: { domains: [], sources: [], freshness_statuses: [] },
  items: [],
};

const EMPTY_COMPATIBILITY = {
  status: 'DEGRADED',
  compatible: 0,
  incompatible: 0,
  missing: 5,
  items: [],
};

function formatDate(value) {
  if (!value) return '—';
  const normalized = String(value).includes('T') ? value : `${value}T00:00:00`;
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).format(new Date(normalized));
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function formatStorage(storage) {
  if (!storage?.schema_name || !storage?.relation_name) return 'Unmapped';
  return `${storage.schema_name}.${storage.relation_name}`;
}

function statusTone(status) {
  const normalized = String(status || 'UNKNOWN').toUpperCase();
  if (
    [
      'CURRENT',
      'SUCCESS',
      'COMPLETED',
      'UPDATED',
      'UNCHANGED',
      'PASS',
      'COMPATIBLE',
    ].includes(normalized)
  ) return 'READY';
  if (['WARNING', 'PARTIAL', 'WARN', 'DEGRADED'].includes(normalized)) return 'WARNING';
  if (
    ['ERROR', 'FAILED', 'FAIL', 'REJECTED', 'BLOCKED', 'INCOMPATIBLE'].includes(normalized)
  ) return 'BLOCKED';
  return 'PLANNED';
}

function CompatibilityStrip({ compatibility }) {
  return (
    <section className="panel contract-strip">
      <div className="contract-strip-summary">
        <div>
          <span className="eyebrow">CONTRACT COMPATIBILITY</span>
          <h2>SkyCommand boundary diagnostics</h2>
        </div>
        <StatusPill status={compatibility.status} tone={statusTone(compatibility.status)} />
      </div>
      <div className="contract-chip-row">
        {compatibility.items.map((item) => (
          <div className="contract-chip" key={item.expected_version}>
            <StatusPill status={item.status} tone={statusTone(item.status)} />
            <strong>{item.expected_version}</strong>
            <small>{item.observed_version || 'Not observed'}</small>
          </div>
        ))}
        {!compatibility.items.length ? (
          <span className="panel-meta">Contract diagnostics are loading…</span>
        ) : null}
      </div>
    </section>
  );
}

function EvidenceList({ title, items, emptyMessage, renderItem }) {
  return (
    <section className="drawer-section">
      <div className="drawer-section-heading">
        <h3>{title}</h3>
        <span>{items.length}</span>
      </div>
      <div className="evidence-list">
        {items.map(renderItem)}
        {!items.length ? <div className="evidence-empty">{emptyMessage}</div> : null}
      </div>
    </section>
  );
}

function AssetDetailDrawer({ detail, state, error, onClose }) {
  if (state === 'IDLE') return null;
  const asset = detail?.asset;
  const freshness = detail?.freshness;

  return (
    <div className="detail-scrim" role="presentation" onMouseDown={onClose}>
      <aside
        aria-label="Asset evidence detail"
        className="asset-detail-drawer"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="drawer-header">
          <div>
            <span className="eyebrow">PHASE 2.2 · QUALITY EVIDENCE</span>
            <h2>{asset?.asset_name || 'Loading asset evidence…'}</h2>
            <p>{asset?.asset_code || 'Contract evidence is being assembled.'}</p>
          </div>
          <button aria-label="Close asset details" type="button" onClick={onClose}>×</button>
        </div>

        {state === 'LOADING' ? <div className="drawer-loading">Loading live evidence…</div> : null}
        {state === 'ERROR' ? (
          <div className="request-error"><strong>Asset evidence unavailable</strong><span>{error}</span></div>
        ) : null}

        {state === 'READY' && detail ? (
          <div className="drawer-body">
            <section className="drawer-status-grid">
              <article>
                <span>Mode</span>
                <StatusPill status={detail.mode} tone={detail.mode === 'LIVE' ? 'READY' : 'WARNING'} />
              </article>
              <article>
                <span>Freshness</span>
                <StatusPill
                  status={freshness.freshness.status_code}
                  tone={statusTone(freshness.freshness.status_code)}
                />
              </article>
              <article>
                <span>Quality Events</span>
                <strong>{detail.totals.quality_events}</strong>
              </article>
              <article>
                <span>Revisions / Rejections</span>
                <strong>{detail.totals.revisions} / {detail.totals.rejections}</strong>
              </article>
            </section>

            <section className="drawer-section">
              <div className="drawer-section-heading"><h3>Asset contract</h3></div>
              <dl className="detail-definition-grid">
                <div><dt>Domain</dt><dd>{asset.domain_code}</dd></div>
                <div><dt>Source</dt><dd>{asset.source?.source_code || 'UNBOUND'}</dd></div>
                <div><dt>Frequency</dt><dd>{asset.frequency_code || '—'}</dd></div>
                <div><dt>Unit</dt><dd>{asset.unit_code || '—'}</dd></div>
                <div><dt>Storage</dt><dd>{formatStorage(asset.storage)}</dd></div>
                <div><dt>Criticality</dt><dd>{asset.criticality_code}</dd></div>
              </dl>
              <p className="detail-message">{asset.asset_description || 'No asset description supplied.'}</p>
            </section>

            <section className="drawer-section">
              <div className="drawer-section-heading"><h3>Freshness evidence</h3></div>
              <p className="detail-message">{freshness.freshness.message}</p>
              <dl className="detail-definition-grid">
                <div><dt>Reason</dt><dd>{freshness.freshness.reason_code}</dd></div>
                <div><dt>Severity</dt><dd>{freshness.freshness.severity_code}</dd></div>
                <div><dt>Source latest</dt><dd>{formatDate(freshness.evidence.source_latest_date)}</dd></div>
                <div><dt>Target latest</dt><dd>{formatDate(freshness.evidence.target_latest_date)}</dd></div>
                <div><dt>Rows</dt><dd>{freshness.evidence.target_row_count?.toLocaleString() || '—'}</dd></div>
                <div><dt>Last attempt</dt><dd>{freshness.evidence.last_attempt_status || '—'}</dd></div>
              </dl>
            </section>

            <section className="drawer-section">
              <div className="drawer-section-heading"><h3>Contract compatibility</h3></div>
              <div className="drawer-contract-list">
                {detail.compatibility.items.map((item) => (
                  <div key={item.expected_version}>
                    <StatusPill status={item.status} tone={statusTone(item.status)} />
                    <span><strong>{item.expected_version}</strong><small>{item.message}</small></span>
                  </div>
                ))}
              </div>
            </section>

            <EvidenceList
              title="Quality events"
              items={detail.quality_events}
              emptyMessage="No quality events were returned for this asset."
              renderItem={(item) => (
                <article className="evidence-card" key={item.quality_event_id || item.created_at}>
                  <div><StatusPill status={item.severity_code} tone={statusTone(item.severity_code)} /><strong>{item.check_code}</strong></div>
                  <p>{item.message}</p>
                  <small>{item.blocking ? 'Blocking' : 'Non-blocking'} · {formatDate(item.created_at)}</small>
                </article>
              )}
            />

            <EvidenceList
              title="Revision evidence"
              items={detail.revisions}
              emptyMessage="No revisions were detected for this asset."
              renderItem={(item) => (
                <article className="evidence-card" key={item.revision_event_id || item.created_at}>
                  <div><StatusPill status="REVISION" tone="WARNING" /><strong>{item.observation_key}</strong></div>
                  <p>{formatValue(item.old_value)} → {formatValue(item.new_value)}</p>
                  <small>Detected {formatDate(item.detected_at)}</small>
                </article>
              )}
            />

            <EvidenceList
              title="Rejected rows"
              items={detail.rejections}
              emptyMessage="No rejected rows were returned for this asset."
              renderItem={(item) => (
                <article className="evidence-card" key={item.rejection_event_id || item.created_at}>
                  <div><StatusPill status={item.severity_code} tone="BLOCKED" /><strong>{item.check_code}</strong></div>
                  <p>{item.message}</p>
                  <small>Row {item.source_row_number || '—'} · {formatDate(item.created_at)}</small>
                </article>
              )}
            />

            <EvidenceList
              title="Recent source runs"
              items={detail.recent_runs}
              emptyMessage="No recent source runs were returned."
              renderItem={(item) => (
                <article className="evidence-card" key={item.ingestion_run_id || item.started_at}>
                  <div><StatusPill status={item.status_code} tone={statusTone(item.status_code)} /><strong>{item.source_code}</strong></div>
                  <p>{item.summary || `${item.mode_code} · ${item.trigger_code}`}</p>
                  <small>{formatDate(item.started_at)} · Quality {item.totals.quality_issue_count}</small>
                </article>
              )}
            />
          </div>
        ) : null}
      </aside>
    </div>
  );
}

function DataAssets() {
  const [workspace, setWorkspace] = useState(EMPTY_WORKSPACE);
  const [compatibility, setCompatibility] = useState(EMPTY_COMPATIBILITY);
  const [requestState, setRequestState] = useState('LOADING');
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    domainCode: '',
    sourceCode: '',
    freshnessStatus: '',
    search: '',
  });
  const [refreshKey, setRefreshKey] = useState(0);
  const [detail, setDetail] = useState(null);
  const [detailState, setDetailState] = useState('IDLE');
  const [detailError, setDetailError] = useState('');

  const query = useMemo(
    () => buildQuery({ ...filters, limit: 100 }),
    [filters],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setRequestState('LOADING');
      setError('');
      Promise.all([
        getJson(`/api/v1/integrations/skycommand/workspace/assets${query}`, {
          signal: controller.signal,
        }),
        getJson('/api/v1/integrations/skycommand/contracts/compatibility', {
          signal: controller.signal,
        }),
      ])
        .then(([workspacePayload, compatibilityPayload]) => {
          setWorkspace(workspacePayload);
          setCompatibility(compatibilityPayload);
          setRequestState('READY');
        })
        .catch((requestError) => {
          if (requestError.name !== 'AbortError') {
            setRequestState('ERROR');
            setError(requestError.message);
          }
        });
    }, 180);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, refreshKey]);

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function clearFilters() {
    setFilters({ domainCode: '', sourceCode: '', freshnessStatus: '', search: '' });
  }

  function inspectAsset(item) {
    setDetail(null);
    setDetailError('');
    setDetailState('LOADING');
    getJson(
      `/api/v1/integrations/skycommand/workspace/assets/${item.domain_code}/${item.asset_code}`,
    )
      .then((payload) => {
        setDetail(payload);
        setDetailState('READY');
      })
      .catch((requestError) => {
        setDetailError(requestError.message);
        setDetailState('ERROR');
      });
  }

  function closeDetail() {
    setDetailState('IDLE');
    setDetail(null);
    setDetailError('');
  }

  return (
    <div className="page-stack">
      <section className="page-intro asset-page-intro">
        <div>
          <span className="eyebrow">PHASE 2.2 · CONTRACT + QUALITY EVIDENCE</span>
          <h1>Data Assets</h1>
          <p>
            Discover trusted post-ingestion assets, inspect contract compatibility,
            and trace freshness, run, revision, rejection, and quality evidence.
          </p>
        </div>
        <div className="connection-card">
          <div className="connection-heading">
            <span className={`connection-dot connection-${workspace.connection.status.toLowerCase()}`} />
            <strong>{workspace.connection.status}</strong>
            <StatusPill status={workspace.mode === 'LIVE' ? 'READY' : 'SCAFFOLDED'} />
          </div>
          <p>{workspace.connection.message}</p>
          <small>
            {(workspace.connection.contract_versions || []).join(' · ') || 'Contract negotiation pending'}
          </small>
        </div>
      </section>

      <section className="asset-metric-grid">
        <article className="metric-card"><span>Discoverable Assets</span><strong>{workspace.totals.assets}</strong><small>Portable catalogue records</small></article>
        <article className="metric-card"><span>Connected Sources</span><strong>{workspace.totals.sources}</strong><small>Observable ingestion providers</small></article>
        <article className="metric-card"><span>Current</span><strong>{workspace.totals.current}</strong><small>Assets meeting freshness policy</small></article>
        <article className="metric-card"><span>Warning / Error</span><strong className={workspace.totals.error ? 'metric-alert' : ''}>{workspace.totals.warning} / {workspace.totals.error}</strong><small>Assets requiring attention</small></article>
        <article className="metric-card"><span>Inactive / Unknown</span><strong>{workspace.totals.inactive} / {workspace.totals.unknown}</strong><small>Non-current classification</small></article>
        <article className="metric-card"><span>Quality Findings</span><strong>{workspace.totals.quality_issues}</strong><small>Latest source-run evidence</small></article>
      </section>

      <CompatibilityStrip compatibility={compatibility} />

      <section className="panel asset-filter-panel">
        <div className="panel-heading">
          <div><span className="eyebrow">CATALOGUE CONTROLS</span><h2>Filter the trusted asset inventory</h2></div>
          <div className="filter-actions">
            <button className="secondary-button" type="button" onClick={clearFilters}>Clear</button>
            <button className="primary-button" type="button" onClick={() => setRefreshKey((key) => key + 1)}>Refresh</button>
          </div>
        </div>
        <div className="asset-filter-grid">
          <label>
            <span>Search</span>
            <input name="search" value={filters.search} onChange={updateFilter} placeholder="Asset code, name, provider…" />
          </label>
          <label>
            <span>Domain</span>
            <select name="domainCode" value={filters.domainCode} onChange={updateFilter}>
              <option value="">All domains</option>
              {workspace.filters.domains.map((code) => <option key={code} value={code}>{code}</option>)}
            </select>
          </label>
          <label>
            <span>Source</span>
            <select name="sourceCode" value={filters.sourceCode} onChange={updateFilter}>
              <option value="">All sources</option>
              {workspace.filters.sources.map((code) => <option key={code} value={code}>{code}</option>)}
            </select>
          </label>
          <label>
            <span>Freshness</span>
            <select name="freshnessStatus" value={filters.freshnessStatus} onChange={updateFilter}>
              <option value="">All statuses</option>
              {workspace.filters.freshness_statuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </label>
        </div>
      </section>

      <section className="panel asset-table-panel">
        <div className="panel-heading">
          <div><span className="eyebrow">TRUSTED INVENTORY</span><h2>Downstream-ready source assets</h2></div>
          <span className="panel-meta">{requestState === 'LOADING' ? 'Refreshing…' : `${workspace.items.length} displayed`}</span>
        </div>

        {error ? <div className="request-error"><strong>Asset workspace unavailable</strong><span>{error}</span></div> : null}

        <div className="asset-table-scroll">
          <table className="asset-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Domain / Source</th>
                <th>Frequency</th>
                <th>Freshness</th>
                <th>Latest Data</th>
                <th>Rows</th>
                <th>Last Run</th>
                <th>Storage</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {workspace.items.map((item) => (
                <tr key={`${item.domain_code}:${item.asset_code}`}>
                  <td>
                    <div className="asset-primary"><strong>{item.asset_name}</strong><code>{item.asset_code}</code></div>
                    <small>{item.asset_kind_code} · {item.contract_version}</small>
                  </td>
                  <td><strong>{item.domain_code}</strong><small>{item.source_code || 'UNBOUND'} · {item.provider_name || 'No provider'}</small></td>
                  <td><strong>{item.frequency_code || '—'}</strong><small>{item.unit_code || 'No unit'}</small></td>
                  <td><StatusPill status={item.freshness_status} tone={statusTone(item.freshness_status)} /><small>{item.freshness_reason}</small></td>
                  <td><strong>{formatDate(item.target_latest_date)}</strong><small>Source {formatDate(item.source_latest_date)}</small></td>
                  <td><strong>{item.target_row_count?.toLocaleString() || '—'}</strong><small>Quality {item.quality_issue_count}</small></td>
                  <td><StatusPill status={item.last_run_status || item.last_attempt_status || 'UNKNOWN'} tone={statusTone(item.last_run_status || item.last_attempt_status)} /><small>{item.last_run_status || item.last_attempt_status || 'No run evidence'}</small></td>
                  <td><code>{item.storage_relation || 'Unmapped'}</code><small>{item.criticality_code}</small></td>
                  <td><button className="table-action" type="button" onClick={() => inspectAsset(item)}>Inspect</button></td>
                </tr>
              ))}
              {!workspace.items.length && requestState !== 'LOADING' ? (
                <tr><td colSpan="9"><div className="table-empty">No assets match the current filters.</div></td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <AssetDetailDrawer
        detail={detail}
        state={detailState}
        error={detailError}
        onClose={closeDetail}
      />
    </div>
  );
}

export default DataAssets;
