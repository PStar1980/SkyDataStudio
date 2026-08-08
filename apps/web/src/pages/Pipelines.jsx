import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import StatusPill from '../components/StatusPill.jsx';
import { buildQuery, getJson, postJson } from '../services/api.js';

const EMPTY_SUMMARY = {
  pipelines: 0,
  versions: 0,
  parameters: 0,
  steps: 0,
  dependencies: 0,
  statuses: {},
  environments: {},
};

const EMPTY_FORM = {
  mappingId: '',
  code: '',
  name: '',
  description: '',
  status: 'READY',
  environment: 'development',
};

const PIPELINE_STATUSES = ['DRAFT', 'READY', 'ACTIVE', 'RETIRED'];

function statusTone(status) {
  if (status === 'READY' || status === 'ACTIVE' || status === 'PUBLISHED') return 'READY';
  if (status === 'RETIRED' || status === 'DISABLED') return 'BLOCKED';
  return 'PLANNED';
}

function safeCode(value) {
  return value.toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

function mappingLabel(mapping) {
  return `${mapping.source_asset.code} → ${mapping.target_asset.code} · ${mapping.name}`;
}

function Pipelines() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [pipelines, setPipelines] = useState({ total: 0, items: [] });
  const [mappings, setMappings] = useState({ total: 0, items: [] });
  const [filters, setFilters] = useState({ search: '', status: '', environment: '' });
  const [form, setForm] = useState(EMPTY_FORM);
  const [formOpen, setFormOpen] = useState(false);
  const [selectedPipeline, setSelectedPipeline] = useState(null);
  const [detailState, setDetailState] = useState('IDLE');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  const pipelineQuery = useMemo(
    () => buildQuery({ ...filters, limit: 250 }),
    [filters],
  );

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getJson('/api/v1/pipelines/summary', { signal: controller.signal }),
      getJson(`/api/v1/pipelines${pipelineQuery}`, { signal: controller.signal }),
      getJson('/api/v1/metadata/mappings?limit=500', { signal: controller.signal }),
    ])
      .then(([summaryPayload, pipelinePayload, mappingPayload]) => {
        setSummary(summaryPayload);
        setPipelines(pipelinePayload);
        setMappings(mappingPayload);
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      });
    return () => controller.abort();
  }, [pipelineQuery, refreshKey]);

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function updateForm(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function selectMapping(event) {
    const mappingId = event.target.value;
    const mapping = mappings.items.find((item) => item.id === mappingId);
    setForm((current) => ({
      ...current,
      mappingId,
      code: current.code || (mapping ? `${safeCode(mapping.target_asset.code)}_PIPELINE` : ''),
      name: current.name || (mapping ? `${mapping.target_asset.name} Pipeline` : ''),
      description: current.description || (mapping
        ? `Transforms ${mapping.source_asset.name} into ${mapping.target_asset.name} using the governed mapping blueprint.`
        : ''),
    }));
  }

  async function submitPipeline(event) {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      const mapping = await getJson(`/api/v1/metadata/mappings/${form.mappingId}`);
      const payload = {
        code: form.code,
        name: form.name,
        description: form.description || null,
        status: form.status,
        environment: form.environment,
        execution_mode: 'LOCAL',
        mapping_id: form.mappingId,
        version_status: 'READY',
        version_notes: 'Phase 4.1 generated pipeline definition from a governed mapping blueprint.',
        parameters: [
          {
            code: 'RUN_DATE',
            name: 'Run Date',
            data_type: 'DATE',
            required: false,
            ordinal_position: 1,
            description: 'Optional logical processing date for replay-safe local execution.',
          },
        ],
        steps: [
          {
            code: 'READ_SOURCE',
            name: `Read ${mapping.source_asset.name}`,
            step_type: 'SQL',
            execution_order: 1,
            mapping_id: mapping.id,
            status: 'READY',
          },
          {
            code: 'TRANSFORM_TARGET',
            name: `Transform ${mapping.target_asset.name}`,
            step_type: 'SQL',
            execution_order: 2,
            mapping_id: mapping.id,
            sql_text: mapping.transformation_expression || null,
            depends_on_codes: ['READ_SOURCE'],
            status: 'READY',
          },
          {
            code: 'VALIDATE_TARGET',
            name: `Validate ${mapping.target_asset.name}`,
            step_type: 'VALIDATION',
            execution_order: 3,
            mapping_id: mapping.id,
            depends_on_codes: ['TRANSFORM_TARGET'],
            status: 'READY',
          },
          {
            code: 'PUBLISH_TARGET',
            name: `Publish ${mapping.target_asset.name}`,
            step_type: 'PUBLISH',
            execution_order: 4,
            mapping_id: mapping.id,
            depends_on_codes: ['VALIDATE_TARGET'],
            status: 'READY',
          },
        ],
      };
      const created = await postJson('/api/v1/pipelines', payload);
      setMessage(`${created.code} registered with version ${created.current_version} and ${created.step_count} steps.`);
      setForm(EMPTY_FORM);
      setFormOpen(false);
      setRefreshKey((value) => value + 1);
      await inspectPipeline(created.id);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function runPipeline(pipeline) {
    setError('');
    setMessage('');
    try {
      const response = await postJson('/api/v1/pipeline-runs', {
        pipeline_id: pipeline.id,
        replay_mode: 'REUSE',
        parameters: {},
      });
      setMessage(response.reused
        ? `${pipeline.code} reused today's replay-safe local proof run.`
        : `${pipeline.code} completed a new local proof run.`);
      navigate('/orchestration/runs');
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function inspectPipeline(pipelineId) {
    setDetailState('LOADING');
    setSelectedPipeline(null);
    try {
      const payload = await getJson(`/api/v1/pipelines/${pipelineId}`);
      setSelectedPipeline(payload);
      setDetailState('READY');
    } catch (requestError) {
      setError(requestError.message);
      setDetailState('IDLE');
    }
  }

  const executableMappings = mappings.items.filter((mapping) => ['READY', 'ACTIVE'].includes(mapping.status));
  const currentVersion = selectedPipeline?.versions?.at(-1) || null;

  return (
    <div className="workspace-page pipeline-page">
      <section className="registry-intro">
        <div>
          <span className="eyebrow">PHASE 4.2 · PIPELINE DEFINITION + LOCAL EXECUTION</span>
          <h1>Pipelines</h1>
          <p>
            Turn governed source-to-target blueprints into versioned processing definitions with parameters,
            typed steps, dependencies, retry controls, and a replay-safe local execution contract with structured run evidence.
          </p>
        </div>
        <div className="registry-actions">
          <button className="primary-button" type="button" onClick={() => setFormOpen((value) => !value)}>
            {formOpen ? 'Close Composer' : 'Create Pipeline'}
          </button>
        </div>
      </section>

      {message ? <div className="workspace-banner success-banner">{message}</div> : null}
      {error ? <div className="workspace-banner error-banner">{error}</div> : null}

      <section className="pipeline-metric-grid">
        <article className="metric-card"><span>PIPELINES</span><strong>{summary.pipelines}</strong><small>Registered processing definitions</small></article>
        <article className="metric-card"><span>VERSIONS</span><strong>{summary.versions}</strong><small>Immutable design snapshots</small></article>
        <article className="metric-card"><span>STEPS</span><strong>{summary.steps}</strong><small>Typed processing primitives</small></article>
        <article className="metric-card"><span>PARAMETERS</span><strong>{summary.parameters}</strong><small>Runtime input contracts</small></article>
        <article className="metric-card"><span>DEPENDENCIES</span><strong>{summary.dependencies}</strong><small>Execution graph edges</small></article>
      </section>

      {formOpen ? (
        <form className="panel pipeline-form" onSubmit={submitPipeline}>
          <div className="panel-heading">
            <div>
              <span className="eyebrow">VERSION 1 BLUEPRINT</span>
              <h2>Generate a pipeline from a governed mapping</h2>
            </div>
            <span className="panel-meta">Local proof execution · materialization remains gated</span>
          </div>
          <div className="pipeline-form-grid">
            <label className="pipeline-wide">
              <span>Mapping blueprint</span>
              <select name="mappingId" value={form.mappingId} onChange={selectMapping} required>
                <option value="">Select a READY or ACTIVE mapping</option>
                {executableMappings.map((mapping) => (
                  <option key={mapping.id} value={mapping.id}>{mappingLabel(mapping)}</option>
                ))}
              </select>
            </label>
            <label><span>Pipeline code</span><input name="code" value={form.code} onChange={updateForm} required /></label>
            <label><span>Pipeline name</span><input name="name" value={form.name} onChange={updateForm} required /></label>
            <label><span>Status</span><select name="status" value={form.status} onChange={updateForm}>{PIPELINE_STATUSES.map((value) => <option key={value}>{value}</option>)}</select></label>
            <label><span>Environment</span><input name="environment" value={form.environment} onChange={updateForm} required /></label>
            <label className="pipeline-wide"><span>Description</span><textarea name="description" value={form.description} onChange={updateForm} rows="3" /></label>
          </div>
          <section className="pipeline-generated-contract">
            <div><span>01</span><strong>READ_SOURCE</strong><small>SQL</small></div>
            <b>→</b>
            <div><span>02</span><strong>TRANSFORM_TARGET</strong><small>SQL</small></div>
            <b>→</b>
            <div><span>03</span><strong>VALIDATE_TARGET</strong><small>VALIDATION</small></div>
            <b>→</b>
            <div><span>04</span><strong>PUBLISH_TARGET</strong><small>PUBLISH</small></div>
          </section>
          <div className="form-footer"><button className="primary-button" type="submit">Register Version 1</button></div>
        </form>
      ) : null}

      <section className="panel pipeline-inventory">
        <div className="panel-heading">
          <div><span className="eyebrow">PIPELINE CATALOGUE</span><h2>Versioned processing definitions</h2></div>
          <span className="panel-meta">{pipelines.total} pipelines</span>
        </div>
        <div className="pipeline-filter-grid">
          <label><span>Search</span><input name="search" value={filters.search} onChange={updateFilter} placeholder="Code, name, description..." /></label>
          <label><span>Status</span><select name="status" value={filters.status} onChange={updateFilter}><option value="">All statuses</option>{PIPELINE_STATUSES.map((value) => <option key={value}>{value}</option>)}</select></label>
          <label><span>Environment</span><select name="environment" value={filters.environment} onChange={updateFilter}><option value="">All environments</option>{Object.keys(summary.environments).map((value) => <option key={value}>{value}</option>)}</select></label>
        </div>
        <div className="asset-table-scroll">
          <table className="asset-table pipeline-table">
            <thead><tr><th>Pipeline</th><th>Mapping</th><th>Version</th><th>Environment</th><th>Status</th><th>Steps</th><th>Parameters</th><th /></tr></thead>
            <tbody>
              {pipelines.items.map((pipeline) => (
                <tr key={pipeline.id}>
                  <td><div className="asset-primary"><strong>{pipeline.name}</strong><code>{pipeline.code}</code></div><small>{pipeline.execution_mode} execution contract</small></td>
                  <td><strong>{pipeline.mapping?.name || 'Unbound'}</strong><small>{pipeline.mapping ? `${pipeline.mapping.source_asset_code} → ${pipeline.mapping.target_asset_code}` : 'No mapping blueprint'}</small></td>
                  <td><strong>v{pipeline.current_version}</strong><small>{pipeline.version_count} version(s)</small></td>
                  <td><strong>{pipeline.environment}</strong><small>Execution profile</small></td>
                  <td><StatusPill status={pipeline.status} tone={statusTone(pipeline.status)} /></td>
                  <td><strong>{pipeline.step_count}</strong><small>typed steps</small></td>
                  <td><strong>{pipeline.parameter_count}</strong><small>runtime inputs</small></td>
                  <td><div className="table-action-group"><button className="table-action" type="button" onClick={() => inspectPipeline(pipeline.id)}>Inspect</button><button className="table-action run-action" type="button" onClick={() => runPipeline(pipeline)}>Run</button></div></td>
                </tr>
              ))}
              {!pipelines.items.length ? <tr><td colSpan="8" className="table-empty">No pipeline definitions match the current filters.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      {detailState !== 'IDLE' ? (
        <div className="drawer-layer">
          <button className="drawer-scrim" type="button" onClick={() => setDetailState('IDLE')} aria-label="Close pipeline detail" />
          <aside className="asset-detail-drawer pipeline-detail-drawer">
            <header className="drawer-header">
              <div><span className="eyebrow">PIPELINE DEFINITION</span><h2>{selectedPipeline?.name || 'Loading pipeline...'}</h2><small>{selectedPipeline?.code}</small></div>
              <button type="button" onClick={() => setDetailState('IDLE')}>×</button>
            </header>
            {detailState === 'LOADING' ? <div className="drawer-loading">Loading version and dependency evidence...</div> : null}
            {selectedPipeline && currentVersion ? (
              <div className="drawer-body">
                <section className="pipeline-contract-card">
                  <div><span>VERSION</span><strong>v{currentVersion.version_number}</strong><small>{currentVersion.status}</small></div>
                  <div><span>ENVIRONMENT</span><strong>{selectedPipeline.environment}</strong><small>{selectedPipeline.execution_mode}</small></div>
                  <div><span>MAPPING</span><strong>{selectedPipeline.mapping?.code || 'UNBOUND'}</strong><small>{selectedPipeline.mapping?.load_strategy || 'No load strategy'}</small></div>
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Execution contract</h3><StatusPill status={selectedPipeline.status} tone={statusTone(selectedPipeline.status)} /></div>
                  <dl className="detail-definition-grid">
                    <div><dt>Versions</dt><dd>{selectedPipeline.version_count}</dd></div>
                    <div><dt>Steps</dt><dd>{currentVersion.step_count}</dd></div>
                    <div><dt>Parameters</dt><dd>{currentVersion.parameter_count}</dd></div>
                    <div><dt>Structured results</dt><dd>{currentVersion.execution_contract.structured_step_results ? 'Required' : 'Optional'}</dd></div>
                  </dl>
                  {selectedPipeline.description ? <p className="detail-message">{selectedPipeline.description}</p> : null}
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Step graph</h3><span>{currentVersion.steps.length}</span></div>
                  <div className="pipeline-step-list">
                    {currentVersion.steps.map((step) => (
                      <article key={step.id}>
                        <div className="pipeline-step-index">{String(step.execution_order).padStart(2, '0')}</div>
                        <div className="pipeline-step-copy">
                          <div><code>{step.code}</code><StatusPill status={step.step_type} tone={step.step_type === 'VALIDATION' ? 'PLANNED' : 'READY'} /></div>
                          <strong>{step.name}</strong>
                          <small>{step.dependencies.length ? `After ${step.dependencies.map((item) => item.depends_on_step_code).join(', ')}` : 'Entry step'} · retry {step.retry_count} · timeout {step.timeout_seconds}s</small>
                          {step.sql_text ? <pre>{step.sql_text}</pre> : null}
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
                <section className="drawer-section">
                  <div className="drawer-section-heading"><h3>Runtime parameters</h3><span>{currentVersion.parameters.length}</span></div>
                  <div className="pipeline-parameter-list">
                    {currentVersion.parameters.map((parameter) => (
                      <article key={parameter.id}><code>{parameter.code}</code><strong>{parameter.data_type}</strong><small>{parameter.required ? 'Required' : 'Optional'} · {parameter.description || 'No description'}</small></article>
                    ))}
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

export default Pipelines;
