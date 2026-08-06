import { useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { buildQuery, getJson, patchJson, postJson, putJson } from '../services/api.js';

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
  mappings: 0,
  field_mappings: 0,
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

const EMPTY_GOVERNANCE = {
  description: '',
  ownerName: '',
  ownerEmail: '',
  classification: 'INTERNAL',
  criticality: 'STANDARD',
  status: 'ACTIVE',
  tags: '',
};

const EMPTY_FIELD = {
  code: '',
  name: '',
  dataType: 'TEXT',
  nullable: true,
  keyField: false,
  classification: '',
  description: '',
};

const LAYERS = ['RAW', 'STAGING', 'INTERMEDIATE', 'MART', 'SEMANTIC', 'REPORT'];

function fieldRowsFromAsset(asset) {
  if (!asset?.fields?.length) return [{ ...EMPTY_FIELD }];
  return asset.fields.map((field) => ({
    code: field.code,
    name: field.name,
    dataType: field.data_type,
    nullable: field.nullable,
    keyField: field.key_field,
    classification: field.classification || '',
    description: field.description || '',
  }));
}

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
  const [drawerState, setDrawerState] = useState('IDLE');
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [governance, setGovernance] = useState(EMPTY_GOVERNANCE);
  const [fieldRows, setFieldRows] = useState([{ ...EMPTY_FIELD }]);

  const query = useMemo(
    () => buildQuery({ ...filters, limit: 250 }),
    [filters],
  );

  useEffect(() => {
    const controller = new AbortController();
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
    setRequestState('LOADING');
    setError('');
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
    setRequestState('SYNCING');
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

  function inspectAsset(assetId) {
    setDrawerState('LOADING');
    setSelectedAsset(null);
    getJson(`/api/v1/metadata/assets/${assetId}`)
      .then((asset) => {
        setSelectedAsset(asset);
        setGovernance({
          description: asset.description || '',
          ownerName: asset.owner_name || '',
          ownerEmail: asset.owner_email || '',
          classification: asset.classification,
          criticality: asset.criticality,
          status: asset.status,
          tags: asset.tags.join(', '),
        });
        setFieldRows(fieldRowsFromAsset(asset));
        setDrawerState('READY');
      })
      .catch((requestError) => {
        setError(requestError.message);
        setDrawerState('ERROR');
      });
  }

  function updateGovernance(event) {
    const { name, value } = event.target;
    setGovernance((current) => ({ ...current, [name]: value }));
  }

  function saveGovernance(event) {
    event.preventDefault();
    if (!selectedAsset) return;
    setError('');
    patchJson(`/api/v1/metadata/assets/${selectedAsset.id}/governance`, {
      description: governance.description.trim() || null,
      owner_name: governance.ownerName.trim() || null,
      owner_email: governance.ownerEmail.trim() || null,
      classification: governance.classification,
      criticality: governance.criticality,
      status: governance.status,
      tags: governance.tags.split(',').map((item) => item.trim()).filter(Boolean),
    })
      .then((asset) => {
        setSelectedAsset(asset);
        setMessage(`${asset.code} governance updated.`);
        setRefreshKey((value) => value + 1);
      })
      .catch((requestError) => setError(requestError.message));
  }

  function updateField(index, name, value) {
    setFieldRows((current) => current.map((field, fieldIndex) => (
      fieldIndex === index ? { ...field, [name]: value } : field
    )));
  }

  function removeField(index) {
    setFieldRows((current) => (
      current.length === 1
        ? [{ ...EMPTY_FIELD }]
        : current.filter((_, fieldIndex) => fieldIndex !== index)
    ));
  }

  function saveFields(event) {
    event.preventDefault();
    if (!selectedAsset) return;
    const fields = fieldRows
      .filter((field) => field.code.trim())
      .map((field, index) => ({
        code: field.code.trim(),
        name: field.name.trim() || null,
        data_type: field.dataType.trim() || 'TEXT',
        ordinal_position: index + 1,
        nullable: field.nullable,
        key_field: field.keyField,
        classification: field.classification || null,
        description: field.description.trim() || null,
      }));
    setError('');
    putJson(`/api/v1/metadata/assets/${selectedAsset.id}/fields`, { fields })
      .then((asset) => {
        setSelectedAsset(asset);
        setFieldRows(fieldRowsFromAsset(asset));
        setMessage(`${asset.code} schema updated with ${asset.field_count} fields.`);
        setRefreshKey((value) => value + 1);
      })
      .catch((requestError) => setError(requestError.message));
  }

  return (
    <div className="page-stack">
      <section className="page-intro registry-intro">
        <div>
          <span className="eyebrow">PHASE 3.2 · PRODUCT BLUEPRINT FOUNDATION</span>
          <h1>Metadata Registry</h1>
          <p>
            Persist source assets and governed data products, then enrich ownership,
            target schemas, source-to-target mappings, and lineage evidence.
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

      <section className="registry-metric-grid registry-metric-grid-eight">
        {[
          ['Assets', summary.assets, 'Registered products'],
          ['Domains', summary.domains, 'Business ownership'],
          ['Systems', summary.systems, 'Source and target platforms'],
          ['Namespaces', summary.namespaces, 'Schemas and logical spaces'],
          ['Fields', summary.fields, 'Documented attributes'],
          ['Dependencies', summary.dependencies, 'Lineage edges'],
          ['Mappings', summary.mappings, 'Transformation blueprints'],
          ['Field maps', summary.field_mappings, 'Column-level lineage'],
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
            <div><span className="eyebrow">MANUAL REGISTRATION</span><h2>Register a portable data product</h2></div>
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
          <table className="asset-table registry-table registry-table-detail">
            <thead><tr><th>Product</th><th>Layer / Type</th><th>Domain</th><th>System / Namespace</th><th>Owner</th><th>Classification</th><th>Tags</th><th>Blueprint</th></tr></thead>
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
                  <td><button className="table-action" type="button" onClick={() => inspectAsset(asset.id)}>Inspect</button></td>
                </tr>
              ))}
              {!assets.items.length && requestState !== 'LOADING' ? <tr><td colSpan="8" className="table-empty">No metadata products match the current filters.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      {drawerState !== 'IDLE' ? (
        <div className="drawer-layer">
          <button className="drawer-scrim" type="button" onClick={() => setDrawerState('IDLE')} aria-label="Close asset blueprint" />
          <aside className="asset-detail-drawer registry-detail-drawer">
            <header className="drawer-header">
              <div><span className="eyebrow">DATA PRODUCT BLUEPRINT</span><h2>{selectedAsset?.name || 'Loading asset...'}</h2><small>{selectedAsset?.code}</small></div>
              <button type="button" onClick={() => setDrawerState('IDLE')}>×</button>
            </header>
            {drawerState === 'LOADING' ? <div className="drawer-loading">Loading governance, schema, and lineage...</div> : null}
            {selectedAsset ? (
              <div className="drawer-body">
                <section className="drawer-status-grid">
                  <article><span>Layer</span><strong>{selectedAsset.layer}</strong></article>
                  <article><span>Asset type</span><strong>{selectedAsset.asset_type}</strong></article>
                  <article><span>Fields</span><strong>{selectedAsset.field_count}</strong></article>
                  <article><span>Mappings</span><strong>{selectedAsset.inbound_mappings.length + selectedAsset.outbound_mappings.length}</strong></article>
                </section>

                <form className="drawer-section drawer-edit-form" onSubmit={saveGovernance}>
                  <div className="drawer-section-heading"><h3>Ownership and governance</h3><StatusPill status={governance.classification} tone="PLANNED" /></div>
                  <div className="drawer-form-grid">
                    <label><span>Owner</span><input name="ownerName" value={governance.ownerName} onChange={updateGovernance} /></label>
                    <label><span>Owner email</span><input name="ownerEmail" type="email" value={governance.ownerEmail} onChange={updateGovernance} /></label>
                    <label><span>Classification</span><select name="classification" value={governance.classification} onChange={updateGovernance}>{['PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED'].map((value) => <option key={value}>{value}</option>)}</select></label>
                    <label><span>Criticality</span><input name="criticality" value={governance.criticality} onChange={updateGovernance} /></label>
                    <label><span>Status</span><input name="status" value={governance.status} onChange={updateGovernance} /></label>
                    <label><span>Tags</span><input name="tags" value={governance.tags} onChange={updateGovernance} /></label>
                    <label className="drawer-wide"><span>Description</span><textarea name="description" value={governance.description} onChange={updateGovernance} rows="3" /></label>
                  </div>
                  <div className="form-footer"><button className="secondary-button" type="submit">Save Governance</button></div>
                </form>

                <form className="drawer-section drawer-edit-form" onSubmit={saveFields}>
                  <div className="drawer-section-heading"><h3>Target schema</h3><button className="secondary-button compact-button" type="button" onClick={() => setFieldRows((current) => [...current, { ...EMPTY_FIELD }])}>Add Field</button></div>
                  <div className="schema-field-list">
                    {fieldRows.map((field, index) => (
                      <div className="schema-field-row" key={`${index}-${field.code}`}>
                        <input value={field.code} onChange={(event) => updateField(index, 'code', event.target.value)} placeholder="FIELD_CODE" />
                        <input value={field.name} onChange={(event) => updateField(index, 'name', event.target.value)} placeholder="Display name" />
                        <input value={field.dataType} onChange={(event) => updateField(index, 'dataType', event.target.value)} placeholder="TEXT" />
                        <label className="mapping-check"><input type="checkbox" checked={field.keyField} onChange={(event) => updateField(index, 'keyField', event.target.checked)} /><span>Key</span></label>
                        <label className="mapping-check"><input type="checkbox" checked={field.nullable} onChange={(event) => updateField(index, 'nullable', event.target.checked)} /><span>Nullable</span></label>
                        <button className="icon-button" type="button" onClick={() => removeField(index)}>×</button>
                      </div>
                    ))}
                  </div>
                  <div className="form-footer"><button className="secondary-button" type="submit">Save Schema</button></div>
                </form>

                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Lineage and mappings</h3><span>{selectedAsset.upstream_dependencies.length + selectedAsset.downstream_dependencies.length}</span></div>
                  <div className="lineage-stack">
                    {selectedAsset.inbound_mappings.map((mapping) => (
                      <article key={mapping.id}><span>UPSTREAM</span><strong>{mapping.source_asset.name} → {selectedAsset.name}</strong><small>{mapping.code} · {mapping.load_strategy} · {mapping.field_mapping_count} fields</small></article>
                    ))}
                    {selectedAsset.outbound_mappings.map((mapping) => (
                      <article key={mapping.id}><span>DOWNSTREAM</span><strong>{selectedAsset.name} → {mapping.target_asset.name}</strong><small>{mapping.code} · {mapping.load_strategy} · {mapping.field_mapping_count} fields</small></article>
                    ))}
                    {!selectedAsset.inbound_mappings.length && !selectedAsset.outbound_mappings.length ? <div className="evidence-empty">No source-to-target mapping has been registered for this asset yet.</div> : null}
                  </div>
                </section>
              </div>
            ) : null}
          </aside>
        </div>
      ) : null}
    </div>
  );
}

export default MetadataRegistry;
