import { useCallback, useEffect, useMemo, useState } from 'react';
import StatusPill from '../components/StatusPill.jsx';
import { getJson } from '../services/api.js';

const EMPTY_CATALOGUE = {
  artifact_status: 'MISSING',
  generated_at: null,
  dbt_version: null,
  model_count: 0,
  ready_model_count: 0,
  source_count: 0,
  test_count: 0,
  models: [],
};

const LAYER_ORDER = { STAGING: 1, INTERMEDIATE: 2, MART: 3 };

function generatedLabel(value) {
  if (!value) return 'Awaiting first dbt artifact';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function statusTone(status) {
  if (status === 'READY') return 'READY';
  if (status === 'ERROR') return 'UNAVAILABLE';
  return 'PLANNED';
}

function dependencyLabel(items) {
  if (!items.length) return 'None';
  return items.map((item) => item.name).join(', ');
}

function DataModels() {
  const [catalogue, setCatalogue] = useState(EMPTY_CATALOGUE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedModel, setSelectedModel] = useState(null);

  const loadCatalogue = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setCatalogue(await getJson('/api/v1/transformations/dbt/models'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getJson('/api/v1/transformations/dbt/models', { signal: controller.signal })
      .then(setCatalogue)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const models = useMemo(
    () => [...catalogue.models].sort((left, right) => (
      (LAYER_ORDER[left.layer] || 99) - (LAYER_ORDER[right.layer] || 99)
      || left.name.localeCompare(right.name)
    )),
    [catalogue.models],
  );
  const allReady = catalogue.model_count > 0
    && catalogue.ready_model_count === catalogue.model_count;

  return (
    <div className="page-stack data-model-page">
      <section className="workspace-intro data-model-intro">
        <div>
          <span className="eyebrow">PHASE 6.2 · DBT MODEL CATALOGUE + ARTIFACT EVIDENCE</span>
          <h1>Data Models</h1>
          <p>
            Read dbt&apos;s generated manifest and run results as runtime evidence, then expose
            model ownership, layer boundaries, tests, columns, and direct dependencies without
            duplicating dbt&apos;s metadata in Studio PostgreSQL.
          </p>
        </div>
        <button className="primary-button" type="button" onClick={loadCatalogue} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh Catalogue'}
        </button>
      </section>

      {error ? <div className="request-error"><span>!</span><strong>{error}</strong></div> : null}

      <section className="metric-grid data-model-metric-grid">
        <article className="metric-card">
          <span>Artifacts</span>
          <strong>{catalogue.artifact_status}</strong>
          <small>{generatedLabel(catalogue.generated_at)}</small>
        </article>
        <article className="metric-card">
          <span>Models</span>
          <strong>{catalogue.ready_model_count}/{catalogue.model_count}</strong>
          <small>{allReady ? 'Latest build evidence is green' : 'Run dbt build to refresh evidence'}</small>
        </article>
        <article className="metric-card">
          <span>Data Tests</span>
          <strong>{catalogue.test_count}</strong>
          <small>Discovered from manifest nodes</small>
        </article>
        <article className="metric-card">
          <span>Sources</span>
          <strong>{catalogue.source_count}</strong>
          <small>Declared dbt source seams</small>
        </article>
        <article className="metric-card">
          <span>dbt Core</span>
          <strong>{catalogue.dbt_version || '—'}</strong>
          <small>Artifact-producing runtime</small>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">MODEL DEPENDENCY GRAPH</span>
            <h2>Artifact-backed staging → intermediate → mart chain</h2>
          </div>
          <StatusPill
            status={allReady ? 'READY' : (catalogue.artifact_status === 'MISSING' ? 'MISSING' : 'FOUNDATION')}
          />
        </div>
        {models.length ? (
          <div className="data-model-flow-grid">
            {models.map((model, index) => (
              <article className="data-model-flow-card" key={model.unique_id}>
                <div>
                  <span>0{index + 1} · {model.layer}</span>
                  <StatusPill status={model.build_status} tone={statusTone(model.build_status)} />
                </div>
                <strong>{model.name}</strong>
                <code>{model.relation}</code>
                <p>{model.description || 'No model description supplied.'}</p>
                <footer>
                  <span>{model.materialization}</span>
                  <span>{model.test_count} tests</span>
                </footer>
                {index < models.length - 1 ? <b aria-hidden="true">→</b> : null}
              </article>
            ))}
          </div>
        ) : (
          <div className="data-model-empty">
            <strong>No dbt manifest is available yet.</strong>
            <span>Run <code>.\scripts\dbt.ps1 build</code>, then refresh this catalogue.</span>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">MODEL INVENTORY</span>
            <h2>Runtime metadata from dbt artifacts</h2>
          </div>
          <span className="panel-count">{models.length} models</span>
        </div>
        <div className="asset-table-scroll">
          <table className="asset-table data-model-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Layer</th>
                <th>Materialization</th>
                <th>Build</th>
                <th>Columns</th>
                <th>Tests</th>
                <th>Upstream</th>
                <th>Downstream</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {models.map((model) => (
                <tr key={model.unique_id}>
                  <td>
                    <div className="asset-primary">
                      <strong>{model.name}</strong>
                      <code>{model.relation}</code>
                    </div>
                    <small>{model.path}</small>
                  </td>
                  <td><StatusPill status={model.layer} /></td>
                  <td><strong>{model.materialization}</strong><small>dbt config</small></td>
                  <td><StatusPill status={model.build_status} tone={statusTone(model.build_status)} /></td>
                  <td><strong>{model.columns.length}</strong><small>documented fields</small></td>
                  <td><strong>{model.test_count}</strong><small>attached assertions</small></td>
                  <td><strong>{model.upstream.length}</strong><small>{dependencyLabel(model.upstream)}</small></td>
                  <td><strong>{model.downstream.length}</strong><small>{dependencyLabel(model.downstream)}</small></td>
                  <td>
                    <button className="table-action" type="button" onClick={() => setSelectedModel(model)}>
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
              {!models.length ? (
                <tr><td colSpan="9" className="table-empty">No models are available from dbt artifacts.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      {selectedModel ? (
        <div className="drawer-layer">
          <button
            className="drawer-scrim"
            type="button"
            onClick={() => setSelectedModel(null)}
            aria-label="Close model detail"
          />
          <aside className="asset-detail-drawer data-model-detail-drawer">
            <header className="drawer-header">
              <div>
                <span className="eyebrow">DBT MODEL</span>
                <h2>{selectedModel.name}</h2>
                <small>{selectedModel.relation}</small>
              </div>
              <button type="button" onClick={() => setSelectedModel(null)}>×</button>
            </header>
            <div className="drawer-body">
              <section className="data-model-contract-card">
                <div><span>LAYER</span><strong>{selectedModel.layer}</strong><small>{selectedModel.materialization}</small></div>
                <div><span>BUILD</span><strong>{selectedModel.build_status}</strong><small>{selectedModel.test_count} tests</small></div>
                <div><span>PATH</span><strong>{selectedModel.path}</strong><small>Project-owned SQL model</small></div>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-heading"><h3>Definition</h3><StatusPill status={selectedModel.build_status} tone={statusTone(selectedModel.build_status)} /></div>
                <p className="detail-message">{selectedModel.description || 'No description supplied in dbt metadata.'}</p>
                <div className="data-model-tag-row">
                  {selectedModel.tags.map((tag) => <span key={tag}>{tag}</span>)}
                  {!selectedModel.tags.length ? <span>no tags</span> : null}
                </div>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-heading"><h3>Direct lineage</h3><span>{selectedModel.upstream.length + selectedModel.downstream.length}</span></div>
                <div className="data-model-lineage-grid">
                  <article>
                    <span>UPSTREAM</span>
                    {selectedModel.upstream.map((item) => (
                      <div key={item.unique_id}><strong>{item.name}</strong><small>{item.resource_type}</small></div>
                    ))}
                    {!selectedModel.upstream.length ? <small>No upstream nodes.</small> : null}
                  </article>
                  <article>
                    <span>DOWNSTREAM</span>
                    {selectedModel.downstream.map((item) => (
                      <div key={item.unique_id}><strong>{item.name}</strong><small>{item.resource_type}</small></div>
                    ))}
                    {!selectedModel.downstream.length ? <small>No downstream nodes.</small> : null}
                  </article>
                </div>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-heading"><h3>Columns</h3><span>{selectedModel.columns.length}</span></div>
                <div className="data-model-column-list">
                  {selectedModel.columns.map((column) => (
                    <article key={column.name}>
                      <code>{column.name}</code>
                      <small>{column.description || 'No column description supplied.'}</small>
                    </article>
                  ))}
                  {!selectedModel.columns.length ? <div className="table-empty">No columns were declared in dbt schema metadata.</div> : null}
                </div>
              </section>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}

export default DataModels;
