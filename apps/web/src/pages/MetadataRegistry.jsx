import { useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { buildQuery, getJson, postJson } from '../services/api.js';

const EMPTY_SUMMARY = {
  status: 'UNAVAILABLE',
  message: 'Waiting for metadata storage.',
  domains: 0,
  systems: 0,
  connections: 0,
  namespaces: 0,
  assets: 0,
  fields: 0,
  dependencies: 0,
  layers: {},
};

const EMPTY_FORM = {
  domainCode: 'OPERATIONS',
  domainName: 'Operations',
  systemCode: 'CRM',
  systemName: 'Customer Relationship Management',
  namespaceCode: 'PUBLIC',
  namespaceName: 'Public',
  code: '',
  name: '',
  layer: 'RAW',
  assetType: 'TABLE',
  physicalName: '',
  ownerName: '',
  classification: 'INTERNAL',
  tags: '',
};

const LAYERS = ['RAW', 'STAGING', 'INTERMEDIATE', 'MART', 'SEMANTIC', 'REPORT'];

function MetadataRegistry() {
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [assets, setAssets] = useState({ total: 0, items: [] });
  const [domains, setDomains] = useState([]);
  const [systems, setSystems] = useState([]);
  const [filters, setFilters] = useState({ search: '', domainCode: '', systemCode: '', layer: '' });
  const [requestState, setRequestState] = useState('LOADING');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [refreshKey, setRefreshKey] = useState(0);

  const query = useMemo(
    () => buildQuery({ ...filters, limit: 250 }),
    [filters],
  );

  useEffect(() => {
    const controller = new AbortController();
    setRequestState('LOADING');
    setError('');
    Promise.all([
      getJson('/api/v1/metadata/summary', { signal: controller.signal }),
      getJson(`/api/v1/metadata/assets${query}`, { signal: controller.signal }),
      getJson('/api/v1/metadata/domains', { signal: controller.signal }),
      getJson('/api/v1/metadata/systems', { signal: controller.signal }),
    ])
      .then(([summaryPayload, assetPayload, domainPayload, systemPayload]) => {
        setSummary(summaryPayload);
        setAssets(assetPayload);
        setDomains(domainPayload);
        setSystems(systemPayload);
        setRequestState('READY');
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') {
          setRequestState('ERROR');
          setError(requestError.message);
        }
      });
    return () => controller.abort();
  }, [query, refreshKey]);

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function updateForm(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function synchronizeSkyCommand() {
    setMessage('');
    setError('');
    setRequestState('SYNCING');
    postJson('/api/v1/metadata/sync/skycommand')
      .then((result) => {
        setMessage(`${result.imported} assets synchronized: ${result.created} created, ${result.updated} updated.`);
        setRefreshKey((value) => value + 1);
      })
      .catch((requestError) => {
        setRequestState('ERROR');
        setError(requestError.message);
      });
  }

  function registerAsset(event) {
    event.preventDefault();
    setMessage('');
    setError('');
    postJson('/api/v1/metadata/assets', {
      domain: { code: form.domainCode, name: form.domainName },
      system: { code: form.systemCode, name: form.systemName },
      namespace: { code: form.namespaceCode, name: form.namespaceName },
      code: form.code,
      name: form.name,
      layer: form.layer,
      asset_type: form.assetType,
      physical_name: form.physicalName || null,
      owner_name: form.ownerName || null,
      classification: form.classification,
      tags: form.tags.split(',').map((item) => item.trim()).filter(Boolean),
    })
      .then((asset) => {
        setMessage(`${asset.code} registered in the ${asset.layer} layer.`);
        setForm(EMPTY_FORM);
        setFormOpen(false);
        setRefreshKey((value) => value + 1);
      })
      .catch((requestError) => setError(requestError.message));
  }

  return (
    <div className="page-stack">
      <section className="page-intro registry-intro">
        <div>
          <span className="eyebrow">PHASE 3.1 · METADATA REGISTRY FOUNDATION</span>
          <h1>Metadata Registry</h1>
          <p>
            Persist source assets and governed data products across domains, systems,
            namespaces, engineering layers, owners, classifications, and tags.
          </p>
        </div>
        <div className="registry-actions">
          <button className="secondary-button" type="button" onClick={() => setFormOpen((open) => !open)}>
            {formOpen ? 'Close Registration' : 'Register Product'}
          </button>
          <button className="primary-button" type="button" onClick={synchronizeSkyCommand}>
            Sync SkyCommand
          </button>
        </div>
      </section>

      {error ? <div className="request-error"><strong>Registry unavailable</strong><span>{error}</span></div> : null}
      {message ? <div className="registry-message">{message}</div> : null}

      <section className="registry-metric-grid">
        {[
          ['Assets', summary.assets, 'Registered products'],
          ['Domains', summary.domains, 'Business ownership'],
          ['Systems', summary.systems, 'Source and target platforms'],
          ['Namespaces', summary.namespaces, 'Schemas and logical spaces'],
          ['Fields', summary.fields, 'Documented attributes'],
          ['Dependencies', summary.dependencies, 'Lineage edges'],
        ].map(([label, value, detail]) => (
          <article className="metric-card" key={label}>
            <span>{label}</span><strong>{value}</strong><small>{detail}</small>
          </article>
        ))}
      </section>

      <section className="panel layer-panel">
        <div className="panel-heading">
          <div><span className="eyebrow">ENGINEERING LAYERS</span><h2>Product inventory by transformation boundary</h2></div>
          <StatusPill status={summary.status} tone={summary.status === 'CONNECTED' ? 'READY' : 'BLOCKED'} />
        </div>
        <div className="layer-grid">
          {LAYERS.map((layer) => (
            <article key={layer}>
              <span>{layer}</span>
              <strong>{summary.layers[layer] || 0}</strong>
            </article>
          ))}
        </div>
      </section>

      {formOpen ? (
        <form className="panel registry-form" onSubmit={registerAsset}>
          <div className="panel-heading">
            <div><span className="eyebrow">MANUAL REGISTRATION</span><h2>Prove a portable non-macro data product</h2></div>
            <span className="panel-meta">No secrets stored</span>
          </div>
          <div className="registry-form-grid">
            {[
              ['domainCode', 'Domain code'], ['domainName', 'Domain name'],
              ['systemCode', 'System code'], ['systemName', 'System name'],
              ['namespaceCode', 'Namespace code'], ['namespaceName', 'Namespace name'],
              ['code', 'Asset code'], ['name', 'Asset name'],
              ['physicalName', 'Physical relation'], ['ownerName', 'Owner'], ['tags', 'Tags (comma-separated)'],
            ].map(([name, label]) => (
              <label key={name}><span>{label}</span><input name={name} value={form[name]} onChange={updateForm} required={['code', 'name'].includes(name)} /></label>
            ))}
            <label><span>Layer</span><select name="layer" value={form.layer} onChange={updateForm}>{LAYERS.map((layer) => <option key={layer}>{layer}</option>)}</select></label>
            <label><span>Asset type</span><select name="assetType" value={form.assetType} onChange={updateForm}>{['TABLE', 'VIEW', 'FILE', 'API', 'MODEL', 'DATASET', 'REPORT', 'TIME_SERIES'].map((type) => <option key={type}>{type}</option>)}</select></label>
            <label><span>Classification</span><select name="classification" value={form.classification} onChange={updateForm}>{['PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED'].map((value) => <option key={value}>{value}</option>)}</select></label>
          </div>
          <div className="form-footer"><button className="primary-button" type="submit">Register Data Product</button></div>
        </form>
      ) : null}

      <section className="panel registry-inventory">
        <div className="panel-heading">
          <div><span className="eyebrow">GOVERNED INVENTORY</span><h2>Studio-owned source assets and data products</h2></div>
          <span className="panel-meta">{assets.total} registered</span>
        </div>
        <div className="registry-filter-grid">
          <label><span>Search</span><input name="search" value={filters.search} onChange={updateFilter} placeholder="Code, name, physical relation..." /></label>
          <label><span>Domain</span><select name="domainCode" value={filters.domainCode} onChange={updateFilter}><option value="">All domains</option>{domains.map((domain) => <option value={domain.code} key={domain.id}>{domain.name}</option>)}</select></label>
          <label><span>System</span><select name="systemCode" value={filters.systemCode} onChange={updateFilter}><option value="">All systems</option>{systems.map((system) => <option value={system.code} key={system.id}>{system.name}</option>)}</select></label>
          <label><span>Layer</span><select name="layer" value={filters.layer} onChange={updateFilter}><option value="">All layers</option>{LAYERS.map((layer) => <option key={layer}>{layer}</option>)}</select></label>
        </div>
        <div className="asset-table-scroll">
          <table className="asset-table registry-table">
            <thead><tr><th>Product</th><th>Layer / Type</th><th>Domain</th><th>System / Namespace</th><th>Owner</th><th>Classification</th><th>Tags</th></tr></thead>
            <tbody>
              {assets.items.map((asset) => (
                <tr key={asset.id}>
                  <td><div className="asset-primary"><strong>{asset.name}</strong><code>{asset.code}</code></div><small>{asset.physical_name || 'Logical product'}</small></td>
                  <td><StatusPill status={asset.layer} tone={asset.layer === 'RAW' ? 'FOUNDATION' : 'READY'} /><small>{asset.asset_type}</small></td>
                  <td><strong>{asset.domain_name}</strong><small>{asset.domain_code}</small></td>
                  <td><strong>{asset.system_name}</strong><small>{asset.namespace_code}</small></td>
                  <td><strong>{asset.owner_name || 'Unassigned'}</strong><small>{asset.field_count} fields</small></td>
                  <td><StatusPill status={asset.classification} tone={asset.classification === 'RESTRICTED' ? 'BLOCKED' : 'PLANNED'} /></td>
                  <td><div className="tag-row">{asset.tags.slice(0, 4).map((tag) => <span key={tag}>{tag}</span>)}</div></td>
                </tr>
              ))}
              {!assets.items.length && requestState !== 'LOADING' ? <tr><td colSpan="7" className="table-empty">No metadata products match the current filters.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default MetadataRegistry;
