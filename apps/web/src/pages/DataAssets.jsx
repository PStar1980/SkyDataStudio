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

function formatDate(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  }).format(new Date(`${value}T00:00:00`));
}

function statusTone(status) {
  const normalized = String(status || 'UNKNOWN').toUpperCase();
  if (['CURRENT', 'SUCCESS', 'COMPLETED', 'UPDATED', 'UNCHANGED', 'PASS'].includes(normalized)) return 'READY';
  if (['WARNING', 'PARTIAL', 'WARN'].includes(normalized)) return 'WARNING';
  if (['ERROR', 'FAILED', 'FAIL', 'REJECTED', 'BLOCKED'].includes(normalized)) return 'BLOCKED';
  return 'PLANNED';
}

function DataAssets() {
  const [workspace, setWorkspace] = useState(EMPTY_WORKSPACE);
  const [requestState, setRequestState] = useState('LOADING');
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    domainCode: '',
    sourceCode: '',
    freshnessStatus: '',
    search: '',
  });
  const [refreshKey, setRefreshKey] = useState(0);

  const query = useMemo(
    () => buildQuery({ ...filters, limit: 100 }),
    [filters],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setRequestState('LOADING');
      setError('');
      getJson(`/api/v1/integrations/skycommand/workspace/assets${query}`, {
        signal: controller.signal,
      })
        .then((payload) => {
          setWorkspace(payload);
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

  return (
    <div className="page-stack">
      <section className="page-intro asset-page-intro">
        <div>
          <span className="eyebrow">PHASE 2.1.5 · FRESHNESS CONTRACT ALIGNMENT</span>
          <h1>Data Assets</h1>
          <p>
            Discover trusted post-ingestion assets, freshness evidence, storage bindings,
            and the latest source-run outcomes through versioned read-only contracts.
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
                </tr>
              ))}
              {!workspace.items.length && requestState !== 'LOADING' ? (
                <tr><td colSpan="8"><div className="table-empty">No assets match the current filters.</div></td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default DataAssets;
