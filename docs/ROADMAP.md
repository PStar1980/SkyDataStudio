# Roadmap Notes

The canonical implementation roadmap is maintained in the root `README.md` so GitHub visitors immediately understand the product direction.

## Phase 1.2 — Green Validation Baseline

**Status:** Complete. Local and GitHub validation are green, and the repository promotion flow is proven.

Changes:

- backend Ruff import and line-length findings repaired;
- JSX component references registered with ESLint without introducing another package dependency;
- mobile navigation state update removed from the pathname effect;
- local validation expanded to Python compilation, dependency synchronization, Ruff, mypy, pytest, ESLint, and Vite build;
- first local validation generates `uv.lock` and `apps/web/package-lock.json`;
- subsequent local and GitHub runs consume locked dependencies;
- GitHub Actions upgraded to current Node 24-compatible action generations;
- GitHub workflow concurrency now cancels superseded validation runs.

Closure evidence:

- local `python scripts/validate.py` succeeds;
- `uv.lock` and `apps/web/package-lock.json` are committed;
- PR and post-merge backend/frontend checks succeed;
- the SkyCommand promotion workflow is proven;
- local and remote `main`/`dev` references synchronize.

This file remains the home for phase-level decisions, acceptance evidence, and closure summaries as development proceeds.

## Phase 2.1 — Live SkyCommand Contract Bridge

**Status:** Live bridge proven; freshness vocabulary alignment is closing the phase.

Changes:

- typed async SkyCommand HTTP client with internal-token, bearer-token, and unauthenticated modes;
- Pydantic consumer models for catalogue domains, sources, assets, freshness, and ingestion runs;
- read-only SkyData API façade under `/api/v1/integrations/skycommand`;
- composite Data Assets workspace joining catalogue, freshness, storage, and recent-run evidence;
- explicit LIVE, PREVIEW, and UNAVAILABLE connection states;
- offline preview fixtures so the workbench remains demonstrable when SkyCommand is stopped;
- SkyCommand internal-service identity extended with `INGESTION_VIEW_STATUS` only;
- repository map/package tools hardened to ignore Python virtual environments and caches.

Proven evidence:

- SkyCommand and SkyData Studio use the same internal API secret locally;
- authorized integration health returns `CONNECTED` and authenticated contract access succeeds;
- Data Assets discovers 69 live assets across three sources;
- offline mode visibly switches to `PREVIEW` rather than masquerading as live data;
- backend Ruff, mypy, and pytest pass;
- frontend ESLint and Vite build pass locally and in GitHub Actions;
- SkyCommand repository map/package self-tests pass;
- both repositories complete normal development promotion and synchronize all four refs.

## Phase 2.1.5 — Freshness Contract Alignment and Bridge Closure

**Status:** Complete. Canonical freshness totals and pills are proven live, validation is green, and the repository promotion completed.

Changes:

- SkyData Studio now uses SkyCommand's canonical freshness status codes: `CURRENT`, `WARNING`, `ERROR`, `INACTIVE`, and `UNKNOWN`;
- workspace totals, preview fixtures, filters, tests, and status pills use the same vocabulary as the live contract;
- freshness pills display the contract status while applying ready, warning, blocked, or neutral visual tones;
- Windows validation automatically uses uv copy mode, avoiding Dropbox-incompatible hard-link behavior;
- Phase 2.1 closure evidence records authenticated live access, 69 discovered assets, explicit preview fallback, green local validation, and green GitHub checks.

Closure evidence:

- live Data Assets totals classify the 69 assets without treating `CURRENT` as `UNKNOWN`;
- row-level pills display canonical freshness status codes;
- preview mode uses the same freshness vocabulary and filters as live mode;
- `python scripts/validate.py` succeeds without manually setting `UV_LINK_MODE`;
- GitHub backend and frontend checks pass;
- local and remote `main`/`dev` references synchronize after promotion.



## Phase 2.2 — Contract Compatibility and Quality Evidence

**Status:** Complete. Contract compatibility, quality evidence, asset inspection, local validation, GitHub checks, and normal promotion are green.

Changes:

- typed `ingestion_quality_evidence.v1` consumers for quality, revision, and rejection events;
- explicit compatibility diagnostics for all five SkyCommand-to-SkyData boundary contracts;
- asset-level evidence endpoint joining catalogue, freshness, recent runs, quality events, revisions, and rejected rows;
- Data Assets compatibility strip and evidence drawer;
- live and preview evidence modes use the same response contracts;
- validation blocks early when FastAPI or Vite is running, preventing dependency synchronization from damaging live local environments.

Closure evidence:

- compatibility diagnostics report all five boundary contracts as `COMPATIBLE`;
- asset inspection opens from the Data Assets table and displays live evidence;
- quality/revision/rejection endpoints validate against `ingestion_quality_evidence.v1`;
- preview mode exposes the same evidence shapes when SkyCommand is offline;
- validation stops with a clear message when FastAPI or Vite is running;
- Ruff, mypy, pytest, ESLint, Vite build, GitHub checks, and normal promotion are green.

## Phase 3.1 — Metadata Registry Foundation

**Status:** Complete. PostgreSQL, live synchronization, portable registration, validation, GitHub checks, and normal promotion are green.

Changes:

- Studio-owned SQLAlchemy metadata model for domains, systems, connections, namespaces, assets, fields, ownership, tags, classifications, and dependencies;
- PostgreSQL migration SQL and a repeatable metadata bootstrap command;
- registry APIs for summary, discovery, inspection, manual product registration, and SkyCommand synchronization;
- idempotent SkyCommand import that maps trusted assets into the `RAW` engineering layer without storing source secrets;
- Metadata Registry workspace with layer metrics, filters, manual portable-product registration, and synchronized inventory;
- platform dashboard and navigation advanced to Phase 3.1.

Closure evidence:

- Docker Desktop uses the WSL 2 backend and `studio-postgres` reports healthy;
- `uv run python scripts/bootstrap_metadata.py` creates the seven registry tables;
- live SkyCommand synchronization imports all 69 trusted assets and a second run updates 69 without duplicates;
- Metadata Registry displays domains, systems, namespaces, engineering layers, ownership, classifications, and tags;
- the non-macro `CUSTOMER_ACCOUNT` MART product is registered under Operations / CRM;
- Ruff, mypy, pytest, ESLint, Vite build, GitHub checks, and normal promotion are green.

## Phase 3.2 — Source-to-Target Mapping and Product Blueprints

**Status:** Complete. Live PostgreSQL blueprint proof, target schema enrichment, durable lineage, validation, and promotion are green.

Changes:

- durable source-to-target mapping and field-mapping persistence;
- mapping type, load strategy, lifecycle status, target grain, business keys, transformation expression, and description contracts;
- target-schema enrichment and automatic `TRANSFORMS` dependency creation when a mapping is registered;
- governance and schema administration APIs for existing metadata assets;
- Source Mappings workbench with mapping composer, field-transformation rows, inventory, filters, and blueprint drawer;
- Metadata Registry asset blueprint drawer for ownership, classifications, target fields, and inbound/outbound lineage;
- additive PostgreSQL migration `0002_source_target_mapping.sql`;
- platform dashboard and navigation advanced to Phase 3.2.

Closure evidence:

- re-running the metadata bootstrap created `metadata_mapping` and `metadata_field_mapping` in the existing database;
- trusted SkyCommand `RAW / DFF` is mapped to Studio-owned `MART / FED_FUNDS_RATE_MART` through `MAP_DFF_TO_FED_FUNDS_RATE_MART`;
- two field mappings persist `OBSERVATION_DATE → OBSERVATION_DATE` and `VALUE → RATE`, with the business key and cast contract preserved;
- target schema enrichment produced the expected two target fields and one durable `TRANSFORMS` dependency;
- Source Mappings reports 1 mapping, 2 field mappings, 1 lineage edge, 0 drafts, and 1 READY/ACTIVE blueprint;
- Metadata Registry reports 71 assets, 2 fields, 1 dependency, 1 mapping, and 2 field maps, with the Federal Funds Rate Mart blueprint showing the enriched target schema;
- direct PostgreSQL queries confirm mapping type `TRANSFORM`, load strategy `MERGE`, status `READY`, source `DFF`, target `FED_FUNDS_RATE_MART`, and both field mappings;
- local validation, GitHub checks, and normal development promotion are green.

## Phase 3.2.2 — Windows Validation Runner and Mapping Workbench Polish

**Status:** Complete.

Changes:

- local and GitHub backend validation invoke pytest through `python -m pytest`, avoiding Windows App Control blocks on the generated `pytest.exe` console launcher while preserving one consistent test entry point;
- validation runner behavior is covered by a focused unit test;
- Phase 3.2 closure proof now includes one live RAW-to-MART blueprint with field mappings, dependency creation, target schema enrichment, and registry evidence end to end.

Closure evidence:

- `python scripts/validate.py` reaches and passes pytest locally under the current Windows policy;
- GitHub backend/frontend validation remains green;
- one live mapping is registered and visible in Source Mappings and Metadata Registry blueprint detail;
- normal SkyCommand development promotion synchronizes `dev` and `main`.

## Phase 4.1 — Pipeline Definition Foundation

**Status:** Implemented; pending local PostgreSQL bootstrap, live pipeline-definition proof, validation, and promotion.

Changes:

- versioned `pipeline_definition` and `pipeline_version` persistence tied optionally to a governed source mapping;
- typed runtime parameters with required/default/ordinal metadata;
- typed `SQL`, `PYTHON`, `VALIDATION`, `DBT`, and `PUBLISH` steps with retry, timeout, source/target, mapping, and execution configuration fields;
- durable step-to-step dependency graph with success-gated edges;
- pipeline summary/list/detail/create APIs under `/api/v1/pipelines`;
- Pipelines workbench that generates a version-1 four-step local design from a READY/ACTIVE mapping and exposes version, parameter, step, and dependency evidence;
- additive PostgreSQL migration `0003_pipeline_definition.sql` and bootstrap model registration;
- platform dashboard and navigation advanced to Phase 4.1 while explicitly keeping execution non-mutating until Phase 4.2.

Acceptance evidence required:

- re-running the metadata bootstrap creates `pipeline_definition`, `pipeline_version`, `pipeline_parameter`, `pipeline_step`, and `pipeline_step_dependency` in the existing Studio database;
- one READY mapping produces a version-1 pipeline with one `RUN_DATE` parameter and four ordered steps;
- dependency proof shows `TRANSFORM_TARGET` after `READ_SOURCE`, `VALIDATE_TARGET` after `TRANSFORM_TARGET`, and `PUBLISH_TARGET` after `VALIDATE_TARGET`;
- pipeline list/detail APIs and the Pipelines workbench display the same version, mapping, parameter, and graph evidence;
- no pipeline execution or target data mutation occurs in Phase 4.1;
- Ruff, mypy, pytest, ESLint, Vite build, GitHub checks, and normal promotion are green.
