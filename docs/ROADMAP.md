# Roadmap Notes

The root `README.md` carries the compact public checklist. This file preserves the detailed phase decisions, acceptance evidence, and closure summaries behind that visitor-facing roadmap.

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

**Status:** Complete. Live workbench, API, PostgreSQL graph proof, validation, and promotion are green.

Changes:

- versioned `pipeline_definition` and `pipeline_version` persistence tied optionally to a governed source mapping;
- typed runtime parameters with required/default/ordinal metadata;
- typed `SQL`, `PYTHON`, `VALIDATION`, `DBT`, and `PUBLISH` steps with retry, timeout, source/target, mapping, and execution configuration fields;
- durable step-to-step dependency graph with success-gated edges;
- pipeline summary/list/detail/create APIs under `/api/v1/pipelines`;
- Pipelines workbench that generates a version-1 four-step local design from a READY/ACTIVE mapping and exposes version, parameter, step, and dependency evidence;
- additive PostgreSQL migration `0003_pipeline_definition.sql` and bootstrap model registration.

Closure evidence:

- Studio PostgreSQL contains the five Phase 4.1 pipeline-definition tables;
- `FED_FUNDS_RATE_PIPELINE` is READY in `development`, bound to `MAP_DFF_TO_FED_FUNDS_RATE_MART`, version 1, with one `RUN_DATE` parameter and four steps;
- `/api/v1/pipelines/summary` reports 1 pipeline, 1 version, 1 parameter, 4 steps, and 3 dependencies;
- list/detail APIs and Postman return the same mapping, version, parameter, execution-contract, and step evidence visible in the UI;
- PostgreSQL dependency proof returns `READ_SOURCE → TRANSFORM_TARGET → VALIDATE_TARGET → PUBLISH_TARGET` with the expected SQL/SQL/VALIDATION/PUBLISH types;
- Phase 4.1 remains non-mutating by design; validation and normal promotion are green.

## Phase 4.2 — Replay-Safe Local Execution and Structured Run Evidence

**Status:** Complete.

Delivered:

- durable `pipeline_run` and `pipeline_step_run` persistence with run status, timing, attempt count, resolved parameters, execution context, result payloads, and error evidence;
- deterministic replay keys derived from pipeline/version/environment/runtime parameters, with explicit `REUSE` and `FORCE_NEW` controls;
- runtime parameter resolution and type coercion, including daily defaulting for the optional `RUN_DATE` contract;
- synchronous local dependency executor with success gates, retry counts, skip evidence, and structured step-result contracts;
- contract-aware proof handlers for trusted-source resolution, mapping resolution, target-schema validation, and publication eligibility;
- run summary/list/detail/create APIs under `/api/v1/pipeline-runs`;
- Pipeline Runs workbench with status metrics, run history, replay controls, and step-level evidence;
- Pipelines workbench Run action wired to the local execution engine;
- additive PostgreSQL migration `0004_pipeline_execution.sql`.

Closure evidence:

- Studio PostgreSQL contains `pipeline_run` and `pipeline_step_run`;
- the DFF pipeline completed four SUCCEEDED steps with a resolved `RUN_DATE`;
- the publish probe returned `ELIGIBLE_NOT_PUBLISHED`, while the run result recorded `data_mutation_applied=false` and `materialization_boundary=PHASE_4_3`;
- repeated safe replay reused the original durable row (observed replay count reached 11 during stress-click proof) without creating duplicate step rows;
- two forced proof runs received distinct keys, producing three durable runs and exactly twelve step rows total (four per physical run);
- PostgreSQL and the UI agreed on the READ/TRANSFORM/VALIDATE/PUBLISH operation evidence and successful status;
- validation was green before the live replay proof.

## Phase 4.3 — Curated Table Materialization Proof

**Status:** Complete. Live data-plane materialization, replay/idempotency proof, validation, and normal promotion are green.

Changes:

- consume SkyCommand's existing governed `time_series_observations.v1` endpoint rather than coupling Studio to SkyCommand implementation tables;
- page trusted source observations through the typed `SkyCommandGateway` and validate the portable observation contract;
- execute the registered `OBSERVATION_DATE → OBSERVATION_DATE` and `VALUE → RATE` mapping in memory with target-type coercion and rejection evidence;
- validate target fields, business keys, duplicate keys, and transformed row readiness before publication;
- create the Studio-owned target schema/table from registered metadata when it does not yet exist;
- execute `MERGE` semantics by business key and persist inserted, updated, unchanged, rejected, published, and final target-row counts;
- mark successful publish results `PUBLISHED`; record `materialization_executed=true` and let `data_mutation_applied` reflect whether the MERGE inserted or updated rows;
- version the local execution engine in the replay-key input so a Phase 4.2 non-mutating proof can never satisfy a Phase 4.3 materialization request;
- expose materialization counters and target relation evidence in the Pipeline Runs drawer;
- advance platform/dashboard navigation to Phase 4.3.

Closure evidence:

- the live DFF run read 26,335 governed observations through SkyCommand's portable API contract and all four steps succeeded;
- Studio PostgreSQL contains `mart.fed_funds_rate` with 26,335 rows spanning 1954-07-01 through 2026-08-06 and zero duplicate `observation_date` keys;
- the first materialization inserted/published 26,335 rows and recorded complete row-level evidence;
- `Replay Safely` reused the durable logical run without performing another materialization;
- a forced new materialization against unchanged source data reported 0 inserted, 0 updated, 26,335 unchanged, 0 rejected, and a stable 26,335-row target;
- Ruff, mypy, pytest, ESLint, Vite build, GitHub checks, and normal promotion are green;
- the post-Phase-4 dependency cleanup replaced the deprecated TestClient transport path with `httpx2`, leaving validation warning-free.

## Phase 5.1 — Airflow Runtime and REST API Foundation

**Status:** Complete.

Scope:

- add an isolated Apache Airflow 3.3 local container stack with its own PostgreSQL metadata database;
- run the API server, scheduler, standalone DAG processor, and triggerer as separate Airflow 3 services;
- keep DAG authoring on the public `airflow.sdk` Task SDK seam;
- configure one local-development JWT signing boundary shared by the Airflow components;
- bind the development Airflow UI/API to loopback and cap LocalExecutor parallelism for a lightweight workstation proof;
- add a typed Studio Airflow client that acquires a SimpleAuthManager development token and consumes REST API v2 only;
- expose component health and the DAG catalogue through `/api/v1/integrations/airflow/summary`;
- replace the Apache Airflow placeholder with a live Studio workbench page;
- keep all Airflow metadata-database access inside Airflow itself.

First acceptance proof:

- `airflow-init` completes database migration successfully;
- API server, scheduler, DAG processor, triggerer, and Airflow PostgreSQL are running;
- `/api/v2/monitor/health` reports healthy core components;
- `skydata_studio_platform_smoke` is visible in Airflow and in the Studio DAG catalogue;
- `/orchestration/airflow` reports the live runtime through the Studio API;
- local validation remains green.

## Phase 5.2 — Airflow Pipeline Batch Proof

**Status:** In progress.

Scope:

- add a dedicated `skydata_studio_fed_funds_rate_pipeline` Airflow DAG for the proven DFF pipeline;
- keep Airflow responsible for durable orchestration while SkyData Studio retains mapping, replay, validation, and materialization authority;
- have the DAG call the public Studio API rather than importing Studio database models or reading Studio PostgreSQL directly;
- derive a stable Studio replay key from the Airflow DAG run ID so Airflow task retries cannot duplicate materialization;
- extend pipeline-run trigger evidence with `AIRFLOW`;
- trigger DAG runs through the authenticated Airflow REST API v2 boundary;
- read DAG-run and task-instance state back through REST API v2 and project it into the Apache Airflow workbench;
- keep the existing local engine available for direct/manual proof and recovery.

Acceptance proof:

- the new DFF DAG is parsed and active in Airflow;
- a Studio-launched Airflow DAG run reaches `SUCCESS`;
- the DAG resolves `FED_FUNDS_RATE_PIPELINE` through the Studio API and executes one replay-safe Studio pipeline run;
- the linked Studio run completes all four pipeline steps with Phase 4.3 materialization evidence;
- Airflow task-instance evidence is visible in SkyData Studio without metadata-database reads;
- rerunning an Airflow task with the same DAG run ID reuses the same Studio replay key;
- local validation and GitHub checks remain green.

