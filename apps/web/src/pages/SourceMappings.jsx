import { useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { buildQuery, getJson, postJson } from '../services/api.js';

const EMPTY_SUMMARY = {
  mappings: 0,
  field_mappings: 0,
  dependencies: 0,
  statuses: {},
  load_strategies: {},
};

const EMPTY_FIELD = {
  sourceFieldCode: '',
  targetFieldCode: '',
  targetDataType: 'TEXT',
  transformationType: 'DIRECT',
  expression: '',
  nullable: true,
  keyField: false,
};

const EMPTY_FORM = {
  sourceAssetId: '',
  targetAssetId: '',
  code: '',
  name: '',
  mappingType: 'TRANSFORM',
  loadStrategy: 'FULL_REPLACE',
  status: 'DRAFT',
  grain: '',
  businessKeys: '',
  description: '',
  transformationExpression: '',
};

const MAPPING_TYPES = ['COPY', 'TRANSFORM', 'AGGREGATE', 'JOIN', 'FILTER', 'PUBLISH'];
const LOAD_STRATEGIES = ['FULL_REPLACE', 'APPEND', 'MERGE', 'INCREMENTAL', 'SNAPSHOT'];
const MAPPING_STATUSES = ['DRAFT', 'READY', 'ACTIVE', 'RETIRED'];
const TRANSFORMATION_TYPES = ['DIRECT', 'RENAME', 'CAST', 'DERIVE', 'AGGREGATE', 'CONSTANT'];

function mappingTone(status) {
  if (status === 'ACTIVE' || status === 'READY') return 'READY';
  if (status === 'RETIRED') return 'BLOCKED';
  return 'PLANNED';
}

function assetLabel(asset) {
  return `${asset.layer} · ${asset.domain_code} · ${asset.code} — ${asset.name}`;
}

function FieldMappingRow({ row, index, onChange, onRemove }) {
  return (
    <div className="field-mapping-row">
      <label>
        <span>Source field</span>
        <input
          value={row.sourceFieldCode}
          onChange={(event) => onChange(index, 'sourceFieldCode', event.target.value)}
          placeholder="SOURCE_COLUMN"
        />
      </label>
      <label>
        <span>Target field</span>
        <input
          value={row.targetFieldCode}
          onChange={(event) => onChange(index, 'targetFieldCode', event.target.value)}
          placeholder="TARGET_COLUMN"
        />
      </label>
      <label>
        <span>Target type</span>
        <input
          value={row.targetDataType}
          onChange={(event) => onChange(index, 'targetDataType', event.target.value)}
          placeholder="TEXT"
        />
      </label>
      <label>
        <span>Transformation</span>
        <select
          value={row.transformationType}
          onChange={(event) => onChange(index, 'transformationType', event.target.value)}
        >
          {TRANSFORMATION_TYPES.map((value) => <option key={value}>{value}</option>)}
        </select>
      </label>
      <label className="field-expression">
        <span>Expression</span>
        <input
          value={row.expression}
          onChange={(event) => onChange(index, 'expression', event.target.value)}
          placeholder="upper(SOURCE_COLUMN)"
        />
      </label>
      <label className="mapping-check">
        <input
          type="checkbox"
          checked={row.keyField}
          onChange={(event) => onChange(index, 'keyField', event.target.checked)}
        />
        <span>Business key</span>
      </label>
      <label className="mapping-check">
        <input
          type="checkbox"
          checked={row.nullable}
          onChange={(event) => onChange(index, 'nullable', event.target.checked)}
        />
        <span>Nullable</span>
      </label>
      <button className="icon-button" type="button" onClick={() => onRemove(index)} aria-label="Remove field mapping">
        ×
      </button>
    </div>
  );
}

function SourceMappings() {
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [assets, setAssets] = useState({ total: 0, items: [] });
  const [mappings, setMappings] = useState({ total: 0, items: [] });
  const [filters, setFilters] = useState({ search: '', status: '' });
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldRows, setFieldRows] = useState([{ ...EMPTY_FIELD }]);
  const [formOpen, setFormOpen] = useState(false);
  const [selectedMapping, setSelectedMapping] = useState(null);
  const [detailState, setDetailState] = useState('IDLE');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  const mappingQuery = useMemo(
    () => buildQuery({ ...filters, limit: 250 }),
    [filters],
  );

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getJson('/api/v1/metadata/mappings/summary', { signal: controller.signal }),
      getJson('/api/v1/metadata/assets?limit=500', { signal: controller.signal }),
      getJson(`/api/v1/metadata/mappings${mappingQuery}`, { signal: controller.signal }),
    ])
      .then(([summaryPayload, assetPayload, mappingPayload]) => {
        setSummary(summaryPayload);
        setAssets(assetPayload);
        setMappings(mappingPayload);
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      });
    return () => controller.abort();
  }, [mappingQuery, refreshKey]);

  function updateFilter(event) {
    const { name, value } = event.target;
    setError('');
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function updateForm(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function updateFieldRow(index, name, value) {
    setFieldRows((current) => current.map((row, rowIndex) => (
      rowIndex === index ? { ...row, [name]: value } : row
    )));
  }

  function removeFieldRow(index) {
    setFieldRows((current) => (
      current.length === 1
        ? [{ ...EMPTY_FIELD }]
        : current.filter((_, rowIndex) => rowIndex !== index)
    ));
  }

  function createMapping(event) {
    event.preventDefault();
    const sourceAsset = assets.items.find((asset) => asset.id === form.sourceAssetId);
    const targetAsset = assets.items.find((asset) => asset.id === form.targetAssetId);
    if (!sourceAsset || !targetAsset) {
      setError('Select both a source asset and a target asset.');
      return;
    }
    if (sourceAsset.id === targetAsset.id) {
      setError('Source and target assets must be different.');
      return;
    }

    setError('');
    setMessage('');
    const normalizedRows = fieldRows
      .filter((row) => row.targetFieldCode.trim())
      .map((row, index) => ({
        source_field_code: row.sourceFieldCode.trim() || null,
        target_field_code: row.targetFieldCode.trim(),
        target_data_type: row.targetDataType.trim() || 'TEXT',
        transformation_type: row.transformationType,
        expression: row.expression.trim() || null,
        ordinal_position: index + 1,
        nullable: row.nullable,
        key_field: row.keyField,
      }));
    const generatedCode = `MAP_${sourceAsset.code}_TO_${targetAsset.code}`;
    postJson('/api/v1/metadata/mappings', {
      code: form.code.trim() || generatedCode,
      name: form.name.trim() || `${sourceAsset.name} to ${targetAsset.name}`,
      source_asset_id: sourceAsset.id,
      target_asset_id: targetAsset.id,
      mapping_type: form.mappingType,
      load_strategy: form.loadStrategy,
      status: form.status,
      grain: form.grain.trim() || null,
      business_keys: form.businessKeys.split(',').map((item) => item.trim()).filter(Boolean),
      description: form.description.trim() || null,
      transformation_expression: form.transformationExpression.trim() || null,
      field_mappings: normalizedRows,
    })
      .then((mapping) => {
        setMessage(`${mapping.code} registered with ${mapping.field_mapping_count} field mappings.`);
        setForm(EMPTY_FORM);
        setFieldRows([{ ...EMPTY_FIELD }]);
        setFormOpen(false);
        setRefreshKey((value) => value + 1);
      })
      .catch((requestError) => setError(requestError.message));
  }

  function inspectMapping(mappingId) {
    setDetailState('LOADING');
    setSelectedMapping(null);
    getJson(`/api/v1/metadata/mappings/${mappingId}`)
      .then((mapping) => {
        setSelectedMapping(mapping);
        setDetailState('READY');
      })
      .catch((requestError) => {
        setError(requestError.message);
        setDetailState('ERROR');
      });
  }

  return (
    <div className="page-stack">
      <section className="page-intro registry-intro">
        <div>
          <span className="eyebrow">PHASE 3.2 · SOURCE-TO-TARGET BLUEPRINTS</span>
          <h1>Source Mappings</h1>
          <p>
            Define governed source-to-target movement, target grain, load strategy,
            field transformations, and durable lineage before pipeline execution begins.
          </p>
        </div>
        <div className="registry-actions">
          <button className="primary-button" type="button" onClick={() => setFormOpen((open) => !open)}>
            {formOpen ? 'Close Blueprint' : 'Create Mapping'}
          </button>
        </div>
      </section>

      {error ? <div className="request-error"><strong>Mapping workbench</strong><span>{error}</span></div> : null}
      {message ? <div className="registry-message">{message}</div> : null}

      <section className="mapping-metric-grid">
        {[
          ['Mappings', summary.mappings, 'Source-to-target specifications'],
          ['Field mappings', summary.field_mappings, 'Column-level transformations'],
          ['Lineage edges', summary.dependencies, 'Durable asset dependencies'],
          ['Draft', summary.statuses.DRAFT || 0, 'Still being designed'],
          ['Ready / Active', (summary.statuses.READY || 0) + (summary.statuses.ACTIVE || 0), 'Eligible for execution design'],
        ].map(([label, value, detail]) => (
          <article className="metric-card" key={label}>
            <span>{label}</span><strong>{value}</strong><small>{detail}</small>
          </article>
        ))}
      </section>

      {formOpen ? (
        <form className="panel mapping-form" onSubmit={createMapping}>
          <div className="panel-heading">
            <div>
              <span className="eyebrow">PRODUCT BLUEPRINT</span>
              <h2>Describe how trusted data becomes an analytical product</h2>
            </div>
            <span className="panel-meta">Dependency created automatically</span>
          </div>
          <div className="mapping-form-grid">
            <label className="mapping-wide">
              <span>Source asset</span>
              <select name="sourceAssetId" value={form.sourceAssetId} onChange={updateForm} required>
                <option value="">Select a trusted source asset</option>
                {assets.items.map((asset) => <option key={asset.id} value={asset.id}>{assetLabel(asset)}</option>)}
              </select>
            </label>
            <label className="mapping-wide">
              <span>Target asset</span>
              <select name="targetAssetId" value={form.targetAssetId} onChange={updateForm} required>
                <option value="">Select an intended target product</option>
                {assets.items.filter((asset) => asset.id !== form.sourceAssetId).map((asset) => (
                  <option key={asset.id} value={asset.id}>{assetLabel(asset)}</option>
                ))}
              </select>
            </label>
            <label><span>Mapping code</span><input name="code" value={form.code} onChange={updateForm} placeholder="Auto-generated when blank" /></label>
            <label><span>Mapping name</span><input name="name" value={form.name} onChange={updateForm} placeholder="Auto-generated when blank" /></label>
            <label><span>Mapping type</span><select name="mappingType" value={form.mappingType} onChange={updateForm}>{MAPPING_TYPES.map((value) => <option key={value}>{value}</option>)}</select></label>
            <label><span>Load strategy</span><select name="loadStrategy" value={form.loadStrategy} onChange={updateForm}>{LOAD_STRATEGIES.map((value) => <option key={value}>{value}</option>)}</select></label>
            <label><span>Status</span><select name="status" value={form.status} onChange={updateForm}>{MAPPING_STATUSES.map((value) => <option key={value}>{value}</option>)}</select></label>
            <label><span>Target grain</span><input name="grain" value={form.grain} onChange={updateForm} placeholder="One row per..." /></label>
            <label><span>Business keys</span><input name="businessKeys" value={form.businessKeys} onChange={updateForm} placeholder="CUSTOMER_ID, AS_OF_DATE" /></label>
            <label className="mapping-wide"><span>Description</span><textarea name="description" value={form.description} onChange={updateForm} rows="3" /></label>
            <label className="mapping-wide"><span>Transformation expression / SQL sketch</span><textarea name="transformationExpression" value={form.transformationExpression} onChange={updateForm} rows="4" placeholder="select ... from ..." /></label>
          </div>
          <div className="mapping-field-header">
            <div><span className="eyebrow">FIELD CONTRACT</span><h3>Target schema and column transformations</h3></div>
            <button className="secondary-button" type="button" onClick={() => setFieldRows((current) => [...current, { ...EMPTY_FIELD }])}>Add Field</button>
          </div>
          <div className="field-mapping-list">
            {fieldRows.map((row, index) => (
              <FieldMappingRow
                key={`${index}-${row.targetFieldCode}`}
                row={row}
                index={index}
                onChange={updateFieldRow}
                onRemove={removeFieldRow}
              />
            ))}
          </div>
          <div className="form-footer"><button className="primary-button" type="submit">Register Mapping Blueprint</button></div>
        </form>
      ) : null}

      <section className="panel mapping-inventory">
        <div className="panel-heading">
          <div><span className="eyebrow">LINEAGE INVENTORY</span><h2>Registered transformation blueprints</h2></div>
          <span className="panel-meta">{mappings.total} mappings</span>
        </div>
        <div className="mapping-filter-grid">
          <label><span>Search</span><input name="search" value={filters.search} onChange={updateFilter} placeholder="Code, name, description..." /></label>
          <label><span>Status</span><select name="status" value={filters.status} onChange={updateFilter}><option value="">All statuses</option>{MAPPING_STATUSES.map((value) => <option key={value}>{value}</option>)}</select></label>
        </div>
        <div className="asset-table-scroll">
          <table className="asset-table mapping-table">
            <thead><tr><th>Mapping</th><th>Source</th><th>Flow</th><th>Target</th><th>Load</th><th>Status</th><th>Fields</th><th /></tr></thead>
            <tbody>
              {mappings.items.map((mapping) => (
                <tr key={mapping.id}>
                  <td><div className="asset-primary"><strong>{mapping.name}</strong><code>{mapping.code}</code></div><small>{mapping.mapping_type}</small></td>
                  <td><strong>{mapping.source_asset.name}</strong><small>{mapping.source_asset.layer} · {mapping.source_asset.code}</small></td>
                  <td><span className="mapping-arrow">→</span></td>
                  <td><strong>{mapping.target_asset.name}</strong><small>{mapping.target_asset.layer} · {mapping.target_asset.code}</small></td>
                  <td><strong>{mapping.load_strategy}</strong><small>{mapping.grain || 'Grain not documented'}</small></td>
                  <td><StatusPill status={mapping.status} tone={mappingTone(mapping.status)} /></td>
                  <td><strong>{mapping.field_mapping_count}</strong><small>mapped columns</small></td>
                  <td><button className="table-action" type="button" onClick={() => inspectMapping(mapping.id)}>Inspect</button></td>
                </tr>
              ))}
              {!mappings.items.length ? <tr><td colSpan="8" className="table-empty">No source-to-target mappings match the current filters.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      {detailState !== 'IDLE' ? (
        <div className="drawer-layer">
          <button className="drawer-scrim" type="button" onClick={() => setDetailState('IDLE')} aria-label="Close mapping detail" />
          <aside className="asset-detail-drawer mapping-detail-drawer">
            <header className="drawer-header">
              <div><span className="eyebrow">MAPPING BLUEPRINT</span><h2>{selectedMapping?.name || 'Loading mapping...'}</h2><small>{selectedMapping?.code}</small></div>
              <button type="button" onClick={() => setDetailState('IDLE')}>×</button>
            </header>
            {detailState === 'LOADING' ? <div className="drawer-loading">Loading source-to-target evidence...</div> : null}
            {selectedMapping ? (
              <div className="drawer-body">
                <section className="mapping-flow-card">
                  <div><span>{selectedMapping.source_asset.layer}</span><strong>{selectedMapping.source_asset.name}</strong><small>{selectedMapping.source_asset.code}</small></div>
                  <span className="mapping-flow-arrow">→</span>
                  <div><span>{selectedMapping.target_asset.layer}</span><strong>{selectedMapping.target_asset.name}</strong><small>{selectedMapping.target_asset.code}</small></div>
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Execution contract</h3><StatusPill status={selectedMapping.status} tone={mappingTone(selectedMapping.status)} /></div>
                  <dl className="detail-definition-grid">
                    <div><dt>Mapping type</dt><dd>{selectedMapping.mapping_type}</dd></div>
                    <div><dt>Load strategy</dt><dd>{selectedMapping.load_strategy}</dd></div>
                    <div><dt>Target grain</dt><dd>{selectedMapping.grain || 'Not documented'}</dd></div>
                    <div><dt>Business keys</dt><dd>{selectedMapping.business_keys.join(', ') || 'None'}</dd></div>
                    <div><dt>Field mappings</dt><dd>{selectedMapping.field_mapping_count}</dd></div>
                    <div><dt>Version</dt><dd>{selectedMapping.attributes.version || 1}</dd></div>
                  </dl>
                  {selectedMapping.description ? <p className="detail-message">{selectedMapping.description}</p> : null}
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Transformation sketch</h3></div>
                  <pre className="mapping-expression">{selectedMapping.transformation_expression || 'No transformation expression documented.'}</pre>
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Field lineage</h3><span>{selectedMapping.field_mappings.length}</span></div>
                  <div className="field-lineage-list">
                    {selectedMapping.field_mappings.map((field) => (
                      <article key={field.id}>
                        <div><code>{field.source_field_code || '∅'}</code><span>→</span><code>{field.target_field_code}</code></div>
                        <strong>{field.target_data_type} · {field.transformation_type}</strong>
                        <small>{field.expression || (field.key_field ? 'Business key' : 'Direct mapping')}</small>
                      </article>
                    ))}
                    {!selectedMapping.field_mappings.length ? <div className="evidence-empty">No field-level mapping has been documented yet.</div> : null}
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

export default SourceMappings;
