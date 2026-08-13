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

**Status:** Complete.

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

Closure evidence:

- the DFF Airflow DAG run `skydata__43c672376a514b3caffdac802b710f40` completed successfully with all four task instances green;
- clearing `execute_studio_pipeline` with downstream tasks selected reran the same DAG run and incremented those Airflow task try numbers from 1 to 2;
- SkyData Studio retained exactly one linked run with replay key `AIRFLOW:skydata__43c672376a514b3caffdac802b710f40`;
- the Studio run count remained stable while its replay count increased to 1, proving task retry reused the logical run instead of creating a duplicate;
- the persisted result retained `materialization_executed = true` and `data_mutation_applied = false`, confirming an idempotent retry did not rematerialize unchanged data;
- the linked Studio run remained `SUCCEEDED` with 4/4 steps and 26,335 unchanged target rows.

## Phase 5.3 — Airflow Schedules and Controlled Backfills

**Status:** Complete.

Scope:

- give the proven DFF DAG a time-based daily schedule so Airflow owns recurring batch cadence;
- derive scheduled and backfill `RUN_DATE` values from Airflow data-interval semantics while preserving explicit manual-run dates;
- expose Airflow backfill creation and history through authenticated REST API v2 only;
- keep backfill policy conservative by default: missing runs only, one active run, and no implicit replay of successful logical dates;
- enforce a bounded local proof window of at most seven calendar days and at most three active backfill runs;
- add a dedicated `Schedules & Backfills` Studio workbench instead of exposing raw Airflow controls alone;
- keep every scheduled/backfill DAG run on the same replay-safe Studio callback and materialization contract proven in Phase 5.2.

Acceptance proof:

- Airflow reparses the DFF DAG with a visible daily timetable and keeps the DAG active;
- `/orchestration/backfills` displays the parsed schedule and live backfill catalogue through the Studio API;
- a one-day controlled backfill created from Studio reaches completion in Airflow;
- the resulting DAG run resolves its `RUN_DATE` from the Airflow interval and creates one linked `AIRFLOW:` Studio run;
- the linked Studio run completes 4/4 steps and preserves idempotent materialization evidence;
- unsafe windows over seven days are rejected before Airflow receives the request;
- local validation and GitHub checks remain green.



Closure evidence:

- the DFF DAG is active on the daily `0 0 * * *` timetable while preserving manual launch support;
- the Studio `Schedules & Backfills` workbench created and recorded a completed one-day Airflow backfill;
- the linked Airflow backfill produced one `AIRFLOW:` Studio run that completed 4/4 pipeline steps with zero failed steps;
- the materialized Federal Funds Rate mart remained replay-safe and idempotent through the scheduled/backfill execution contract;
- an oversized local proof window was rejected with HTTP 422 before Airflow accepted a backfill request;
- the shared frontend API error normalizer renders the guardrail as `Local proof backfills are limited to a 7-day window.`;
- Ruff, mypy, 46 pytest tests, npm CI, ESLint, and Vite build are green after the guardrail proof.

## Phase 5.4 — Ingestion-Complete Event Trigger

**Status:** Complete.

Scope:

- declare a DFF ingestion-complete Airflow asset and combine it with the existing daily timetable;
- resolve the latest terminal successful SkyCommand `MACRO/FRED/DFF` ingestion run through the existing read-only contract bridge;
- emit the completion signal through Airflow REST API v2 asset events rather than manually triggering the DAG;
- carry ingestion-run identity and run-date evidence into the existing replay-safe Studio callback;
- deduplicate repeated signals for the same SkyCommand ingestion run by reusing the previously emitted Airflow asset event;
- project asset-event registration, ingestion eligibility, event identity, and resulting DAG-run evidence into the Apache Airflow workbench;
- keep SkyCommand as ingestion authority, Airflow as orchestration authority, and Studio as transformation/materialization authority.

Acceptance proof:

- Airflow reparses the DFF DAG with both the daily timetable and the DFF ingestion-complete asset dependency;
- Studio identifies an eligible terminal successful SkyCommand FRED/DFF ingestion run;
- `Emit Ingestion Event` creates one Airflow asset event through REST API v2;
- Airflow schedules the DFF DAG from that asset event without using the manual DAG-run endpoint;
- the resulting Studio run is `AIRFLOW` triggered, completes 4/4 steps, and preserves Phase 4.3 materialization evidence;
- emitting the same SkyCommand ingestion run a second time reuses the existing asset event and does not create duplicate orchestration;
- local validation and GitHub checks remain green.


Closure evidence:

- Studio resolved terminal successful SkyCommand FRED/DFF ingestion run `6c1adaad-ebe5-4536-bad1-165a6471a581`;
- Airflow registered `x-skycommand://ingestion/macro/dff` and accepted asset event `#1`;
- the native event created Airflow asset-triggered DAG run `asset_triggered__2026-08-10T23:56:51.944633+00:00_RvPL91Wa` without using the manual DAG-run endpoint;
- the linked Studio run completed 4/4 steps with zero failed steps and preserved idempotent 26,335-row materialization evidence;
- replaying the same ingestion signal reused asset event `#1` instead of creating duplicate orchestration;
- the daily scheduled Airflow run continued to execute through the same contract after the asset-triggered proof;
- Ruff, mypy, 49 pytest tests, npm CI, ESLint, and Vite build remained green.

## Phase 6.1 — dbt Runtime and Layered Model Foundation

**Status:** Complete.

Scope:

- run dbt as an ephemeral Docker/Compose workload instead of adding dbt packages to the FastAPI application environment;
- pin the container to dbt Core 1.12.0 and dbt-postgres 1.11.0;
- use the Phase 4.3 `mart.fed_funds_rate` relation as the governed dbt source seam;
- create explicit `dbt_staging`, `dbt_intermediate`, and `dbt_mart` schemas so dbt-owned relations cannot collide with the pipeline materializer;
- build `stg_fed_funds_rate`, `int_fed_funds_rate_changes`, and `fct_fed_funds_rate_daily`;
- add source/model key, nullability, accepted-value, and rate-reasonableness tests;
- expose dbt relation readiness and row-count evidence through `/api/v1/transformations/dbt/summary`;
- replace the Transformations placeholder with a live Phase 6.1 workbench;
- preserve ingestion ownership in SkyCommand, orchestration ownership in Airflow, materialization ownership in the Studio pipeline engine, and analytical modelling ownership in dbt.

Acceptance proof:

- `docker compose -f .\infra\docker-compose.yml build dbt` builds the pinned dbt runtime;
- `.\scripts\dbt.ps1 debug` resolves the Studio PostgreSQL target;
- `.\scripts\dbt.ps1 build` completes with all three models and all fourteen data tests green;
- `dbt_staging.stg_fed_funds_rate`, `dbt_intermediate.int_fed_funds_rate_changes`, and `dbt_mart.fct_fed_funds_rate_daily` exist and retain the 26,335-row proof grain;
- the Transformations workbench reports 3/3 models and 3/3 layers ready;
- local validation and GitHub checks remain green.

Closure evidence:

- the dbt image builds with Git available inside the isolated Python 3.12 runtime;
- `.\scripts\dbt.ps1 debug` resolves the `studio-postgres` target and reports all checks passed;
- `.\scripts\dbt.ps1 build` completes 3 model builds plus 14 data tests with `PASS=17`, `WARN=0`, `ERROR=0`, and `SKIP=0`;
- `dbt_staging.stg_fed_funds_rate`, `dbt_intermediate.int_fed_funds_rate_changes`, and `dbt_mart.fct_fed_funds_rate_daily` each retain the 26,335-row proof grain;
- `/api/v1/transformations/dbt/summary` reports 3/3 models and 3/3 layers ready with all four source/model relations available;
- the Transformations workbench displays the complete source → staging → intermediate → mart chain as READY;
- the PowerShell helper no longer shadows the automatic `$args` variable, and the Windows `RemoteSigned` proof is documented by explicitly unblocking the trusted local helper when required;
- local validation completes with 50 pytest tests, clean Ruff/mypy, zero npm vulnerabilities, clean ESLint, and a successful Vite production build.

## Phase 6.2 — dbt Model Catalogue and Artifact Evidence

**Status:** Complete.

Scope:

- treat dbt `manifest.json` and `run_results.json` as generated runtime evidence rather than duplicating dbt-owned metadata in Studio PostgreSQL;
- expose model name, layer, physical relation, materialization, path, description, tags, documented columns, attached data-test count, and latest build status through a typed Studio API;
- project direct upstream source/model dependencies and downstream model dependencies from the dbt manifest;
- replace the Data Models placeholder with a live artifact-backed catalogue and model-inspection drawer;
- preserve the Phase 6.1 Transformations page as physical-relation readiness evidence while Data Models becomes the logical dbt metadata surface;
- keep generated dbt artifacts ignored by Git and require a local `dbt build` to refresh runtime evidence.

Acceptance proof:

- `GET /api/v1/transformations/dbt/models` reports `artifact_status=READY` after a successful dbt build;
- the API discovers exactly 3 enabled Studio models, 1 declared source, and 14 data tests from the generated artifacts;
- all three model build statuses resolve to READY from `run_results.json`;
- the Data Models workbench displays the staging → intermediate → mart dependency chain and exposes model detail for tags, columns, tests, and direct lineage;
- removing/cleaning the dbt target produces an explicit MISSING artifact state rather than stale or fabricated metadata;
- local validation and GitHub checks remain green.

Closure evidence:

- `GET /api/v1/transformations/dbt/models` reports `artifact_status=READY`, dbt Core 1.12.0, 3 discovered models, 3 ready models, 1 source, and 14 data tests;
- the Data Models workbench displays the complete staging → intermediate → mart graph as READY and exposes the same three models in the runtime inventory;
- model-level test evidence resolves to 3 staging tests, 3 intermediate tests, and 5 mart tests, with the remaining 3 tests attached directly to the curated source;
- direct lineage resolves `fed_funds_rate → stg_fed_funds_rate → int_fed_funds_rate_changes → fct_fed_funds_rate_daily`;
- local validation completes with 52 pytest tests, clean Ruff/mypy, zero npm vulnerabilities, clean ESLint, and a successful Vite production build.

## Phase 6.3 — dbt Semantic Model and Governed Metric Foundation

**Status:** Complete. Semantic parsing, MetricFlow time-spine support, artifact projection, validation, and the workbench proof are green.

Scope:

- adopt dbt Core 1.12's model-embedded semantic YAML specification on the governed Federal Funds Rate mart;
- add a dedicated daily MetricFlow time spine so time-based semantic parsing and aggregation have a continuous DAY-grain calendar;
- define `fed_funds_rate_daily` as the first Studio semantic model without creating a second semantic metadata store;
- add a stable `observation_key` primary entity while preserving the proven one-row-per-day mart grain;
- expose `observation_date`, `observation_month`, `observation_year`, and `rate_direction` as governed semantic dimensions;
- define four simple governed metrics: average rate, minimum rate, maximum rate, and distinct observation count;
- project parsed semantic-model and metric evidence from dbt artifacts through `GET /api/v1/transformations/dbt/semantic`;
- replace the Semantic Layer placeholder with an artifact-backed workbench for semantic models, entities, dimensions, and metrics;
- keep Phase 6.3 limited to portable definitions and artifact evidence rather than claiming a hosted dbt Semantic Layer query service.

Acceptance proof:

- `./scripts/dbt.ps1 build` completes 4 physical dbt models (3 business models plus 1 semantic utility time spine) and 14 data tests with `PASS=18`, `WARN=0`, `ERROR=0`, and `SKIP=0`;
- the generated dbt manifest contains exactly 1 Studio semantic model and 4 Studio metrics;
- `GET /api/v1/transformations/dbt/semantic` reports `artifact_status=READY`, 1 semantic model, 4 metrics, 1 entity, and the expected dimensions;
- the Semantic Layer workbench displays the governed model, primary entity, dimensions, and all four metrics from the generated artifact evidence;
- `dbt_mart.fct_fed_funds_rate_daily` retains 26,335 rows, `dbt_mart.time_spine_daily` exists at DAY granularity, and the business-model Data Models workbench remains 3/3 ready because semantic utility models are excluded from that catalogue;
- local validation and GitHub checks remain green.

Closure evidence:

- `./scripts/dbt.ps1 build` discovers 4 models, 14 data tests, 1 source, 4 metrics, and 1 semantic model, then completes with `PASS=18`, `WARN=0`, `ERROR=0`, and `SKIP=0`;
- the semantic endpoint reports `artifact_status=READY`, 1 semantic model, 4 governed metrics, 1 primary entity, and 4 dimensions;
- the Data Models workbench remains 3/3 READY while the dedicated `time_spine_daily` semantic utility is excluded from the business-model catalogue;
- the Semantic Layer workbench renders the governed model, entity, dimensions, and all four metric definitions from dbt artifacts;
- local validation completes with 57 pytest tests, clean Ruff/mypy, zero npm vulnerabilities, clean ESLint, and a successful Vite production build.

## Phase 7.1 — dbt Quality Evidence and Trust Posture Foundation

**Status:** Complete. Artifact projection, trust posture, workbench proof, strict typing, and local validation are green.

Scope:

- keep dbt as the single authority for test definitions and execution outcomes;
- join test metadata from `target/manifest.json` with latest statuses, failures, messages, and timings from `target/run_results.json`;
- classify checks into completeness, uniqueness, validity, referential-integrity, business-rule, and other quality dimensions;
- resolve every check to its owning source/model, engineering layer, column when applicable, severity, and latest result;
- compute one latest-run trust posture: `TRUSTED`, `DEGRADED`, `BLOCKED`, or `PENDING`;
- expose the evidence through `GET /api/v1/quality/dbt/summary`;
- replace the Data Quality placeholder with an artifact-backed quality workbench and layer coverage view;
- keep Phase 7.1 observational: durable incidents, blocking policies, reconciliation rules, acknowledgements, and SLOs remain later Phase 7 slices.

Closure evidence:

- the quality API reports `artifact_status=READY`, `trust_posture=TRUSTED`, 14 checks, 14 passes, 0 warnings, 0 failures, 0 errors, and the expected 3 source / 11 model split;
- the Data Quality workbench shows TRUSTED with 14 checks, 14 passes, 0 blocking results, and SOURCE 3/3, STAGING 3/3, INTERMEDIATE 3/3, MART 5/5 coverage;
- generic and singular test rows preserve quality dimension, target, layer, column, severity, runtime, path, and result evidence;
- strict mypy typing for normalized quality status is green after replacing an `Any` return with a typed `QualityStatus` lookup;
- Ruff import organization, mypy, 60 pytest tests, npm audit, ESLint, and Vite production build all pass in the final local validation.

## Phase 7.2 — Quality Contract Gate and Consumer Compatibility Workbench

**Status:** Complete. Source-controlled gate evaluation, consumer compatibility, workbench proof, React lint cleanup, and local validation are green.

Scope:

- add a source-controlled quality-contract boundary under `contracts/quality` rather than persisting duplicate dbt test metadata;
- define the first governed mart contract for `fct_fed_funds_rate_daily` with stable selectors for completeness, uniqueness, validity, and business-rule evidence;
- require a 100% pass rate across five consumer-critical MART rules using `BLOCK` enforcement;
- evaluate contract selectors against the latest Phase 7.1 dbt quality evidence and classify the gate as `COMPLIANT`, `DEGRADED`, `BLOCKED`, or `PENDING`;
- expose the evaluation through `GET /api/v1/quality/contracts/summary`;
- replace the Contracts placeholder with a workbench that shows both Studio-owned quality policy and existing SkyCommand consumer contract compatibility;
- keep durable incidents, acknowledgement/remediation ownership, historical SLOs, and reconciliation state outside this slice.

Closure evidence:

- the live quality-contract API reports `COMPLIANT`, 5/5 required rules satisfied, 100% pass rate, 0 blocking rules, 0 missing rules, and READY/TRUSTED underlying dbt evidence;
- the five rules resolve to MART observation-date completeness, rate completeness, observation-date uniqueness, rate-direction validity, and the singular rate-reasonableness assertion;
- the Contracts workbench displays all five quality rules as PASS and all five SkyCommand consumer boundary contracts as COMPATIBLE without merging ownership between the two systems;
- missing latest dbt evidence remains `PENDING`, while a missing or non-passing required selector blocks the contract under `BLOCK` enforcement;
- the React initial-fetch pattern was aligned with the rest of Studio so `react-hooks/set-state-in-effect` remains green;
- final local validation passes Ruff, mypy across 51 source files, 64 pytest tests, npm audit with zero vulnerabilities, ESLint, and Vite production build.

## Phase 7.3 — Durable Quality Incidents and Remediation Lifecycle

**Status:** Complete. Additive incident persistence, clean-evidence reconciliation, lifecycle proof, workbench proof, and local validation are green.

Scope:

- add Studio-owned `quality_incident` and `quality_incident_event` persistence while keeping dbt and source-controlled quality contracts as the upstream evidence/policy authorities;
- reconcile `WARN`, `BLOCK`, and `MISSING` contract-rule outcomes into one durable incident per contract rule;
- preserve OPEN, ACKNOWLEDGED, RESOLVED, and REOPENED lifecycle evidence with operator identity, notes, timestamps, and occurrence count;
- auto-resolve active incidents when the corresponding rule returns to PASS;
- reopen a resolved incident when failing evidence returns, rather than creating duplicate incident rows;
- expose summary, reconciliation, acknowledgement, and manual-resolution APIs under `/api/v1/quality/incidents`;
- add a Quality Incidents workbench while explicitly creating no fake incident when the current contract remains clean;
- keep historical SLO calculation, notification routing, and cross-product lineage impact outside this slice.

Closure evidence:

- re-running `uv run python scripts/bootstrap_metadata.py` reported the Studio metadata schema ready against the existing PostgreSQL database;
- reconciling the live COMPLIANT 5/5 Federal Funds Rate contract returned `created_count=0`, `reopened_count=0`, `resolved_count=0`, zero active incidents, and no synthetic failure record;
- the Quality Incidents API and workbench both showed COMPLIANT/READY with 0 active, 0 blocking, 0 resolved, and an intentionally empty durable register;
- backend lifecycle tests prove BLOCK → OPEN, operator acknowledgement, manual/PASS-driven resolution, and recurrence → REOPENED with occurrence history;
- a Ruff import-order finding in the new lifecycle test was auto-fixed, after which final validation passed Ruff, mypy across 53 source files, 68 pytest tests, npm audit with zero vulnerabilities, ESLint, and Vite production build.



## Phase 7.4 — Quality SLO and Reliability History

**Status:** Complete. Idempotent capture, rolling SLO posture, durable observation history, and local validation are green.

Scope:

- extend the source-controlled Federal Funds Rate quality contract with a 30-day reliability window and 99% minimum compliant-observation target;
- persist `quality_slo_observation` as Studio-owned operational history while leaving dbt test definitions and contract rules at their existing authorities;
- key observations by contract version plus dbt invocation identity so repeated reconciliation of identical evidence is idempotent;
- capture contract status, artifact/trust posture, pass rate, and active/blocking/warning incident totals for each observed evidence invocation;
- compute rolling `MEETING`, `AT_RISK`, `BREACHED`, or `PENDING` posture, compliance rate, outcome counts, and current compliant streak;
- expose `GET /api/v1/quality/reliability/summary` and `POST /api/v1/quality/reliability/capture`;
- make normal incident reconciliation capture reliability evidence automatically, while the dedicated capture endpoint remains a self-contained workbench action;
- add a Quality Reliability workbench and keep scheduled capture cadence, notification routing, and continuous-uptime claims outside this slice.

Acceptance proof:

- re-running the idempotent metadata bootstrap creates `quality_slo_observation` in existing Studio PostgreSQL;
- the first capture of the current clean dbt invocation creates exactly one observation; repeating capture against the same invocation reports `observation_created=false` and leaves history unchanged;
- the live reliability summary reports `MEETING`, a 30-day window, 99% target, 100% observed compliance, 1 compliant observation, 0 blocked observations, and a clean streak of 1;
- the Reliability workbench presents the SLO target, current contract state, rolling posture, and invocation-level observation history;
- backend tests prove idempotent capture, clean SLO success, blocking-observation breach, and pending-before-first-capture behavior;
- local validation remains green with 72 pytest tests plus Ruff, mypy, npm audit, ESLint, and Vite build.

Closure evidence:

- re-running `uv run python .\scripts\bootstrap_metadata.py` reported the existing Studio PostgreSQL metadata schema ready with the additive SLO observation table available;
- the first reliability capture created one observation for the latest dbt invocation and reported `MEETING`, a 30-day window, 99% target, 100% observed compliance, one compliant observation, zero blocked/degraded/pending observations, and a clean streak of one;
- repeating capture against the same dbt invocation returned `observation_created=false` and preserved a single observation, proving replay-safe history;
- the standalone reliability summary returned the same `MEETING` / 100% posture; the PowerShell `ConvertTo-Json -Depth 1` truncation warning was a display-depth warning only and not a service failure;
- final local validation passed Ruff, mypy across 54 source files, 72 pytest tests, npm audit with zero vulnerabilities, ESLint, and Vite production build.

## Phase 8.1 — Cross-Layer Lineage Graph and Impact Radius Foundation

**Status:** Complete. Live graph proof, transitive impact evidence, and final local validation are green.

Scope:

- compose one read-only lineage graph from existing Studio metadata mappings, dbt model dependencies, dbt semantic models, and governed metrics without creating a duplicate lineage authority;
- bridge the registered `DFF → FED_FUNDS_RATE_MART` source-to-target mapping to the governed dbt `fed_funds_rate` source seam;
- preserve dbt source → staging → intermediate → mart edges directly from artifact dependency metadata;
- connect the mart to the `fed_funds_rate_daily` semantic model and its four governed metrics;
- expose typed graph evidence through `GET /api/v1/lineage/summary`;
- compute transitive downstream impact for any selected node through `GET /api/v1/lineage/impact?nodeId=...`;
- replace the Lineage placeholder with an interactive graph and downstream-impact workbench;
- keep field-level lineage, quality/incident overlays, Airflow/pipeline execution lineage, and report/Power BI consumers outside this first Phase 8 slice.

Acceptance proof:

- the live lineage API reports `artifact_status=READY`, one READY Studio metadata mapping, 3 dbt business models, 1 semantic model, and 4 governed metrics;
- the Federal Funds Rate proof composes 11 nodes and 10 directed edges from SkyCommand `DFF` through the Studio curated mart, dbt model DAG, semantic model, and four metrics;
- the default `DFF` impact radius reaches 10 downstream nodes including all 3 dbt models, 1 semantic model, and 4 metrics;
- selecting `int_fed_funds_rate_changes` limits impact to the downstream fact model, semantic model, and four metrics rather than reporting upstream nodes;
- missing dbt artifacts degrade the graph to `PARTIAL` while preserving registered Studio mapping evidence instead of fabricating model lineage;
- the Lineage workbench renders the federated graph and recomputes downstream impact when a node is selected;
- local validation remains green with 76 pytest tests plus Ruff, mypy, npm audit, ESLint, and Vite build.

Closure evidence:

- `GET /api/v1/lineage/summary` returned `artifact_status=READY`, 1 metadata mapping, 3 dbt models, 1 semantic model, 4 metrics, 11 nodes, and 10 edges;
- the default DFF impact radius returned 10 downstream nodes, 3 affected dbt models, 1 semantic model, and 4 governed metrics;
- the Phase 8.1 Ruff line-length cleanup changed formatting only;
- final local validation passed Ruff, mypy across 57 source files, 76 pytest tests, npm audit with zero vulnerabilities, ESLint, and Vite production build.

## Phase 8.2 — Field-Level Lineage and Column Impact Foundation

**Status:** Complete. Field graph proof, metric impact separation, and final local validation are green.

Scope:

- preserve the Phase 8.1 asset/model/semantic/metric graph and add a separate field-level read model rather than persisting a second lineage authority;
- use existing Studio field-mapping rows as the source-to-curated field authority for `OBSERVATION_DATE → OBSERVATION_DATE` and `VALUE → RATE`;
- declare dbt derived-column inputs beside model definitions through column `meta.lineage_inputs`, then read those declarations from generated `manifest.json`;
- expand intermediate and mart column documentation so every field in the proof has an explicit lineage declaration;
- bind final mart fields to governed metrics through dbt metric expressions rather than introducing a Studio-owned semantic dependency table;
- expose `GET /api/v1/lineage/fields/summary` and `GET /api/v1/lineage/fields/impact?fieldId=...`;
- extend the Lineage workbench with grouped field nodes and transitive field-impact evidence;
- keep quality overlays, Airflow runtime lineage, and report/Power BI consumers outside this field-level foundation.

Acceptance proof:

- a fresh `dbt build` remains green and regenerates manifest column annotations while retaining 4 models, 14 data tests, 4 metrics, and 1 semantic model;
- the field lineage API reports `artifact_status=READY`, 2 Studio field mappings, 18 annotated dbt business-model columns, 4 metric bindings, 28 nodes, and 27 directed edges;
- selecting `DFF.value` reaches 15 downstream nodes including rate-derived columns and exactly 3 rate metrics;
- selecting `DFF.observation_date` reaches the observation-key path and observation-count metric without falsely reporting rate metrics;
- the Phase 8.1 asset graph remains READY at 11 nodes / 10 edges;
- local validation remains green with 80 pytest tests plus Ruff, mypy, npm audit, ESLint, and Vite build.

Closure evidence:

- a fresh dbt build completed `PASS=18 WARN=0 ERROR=0 SKIP=0` with 4 models, 14 data tests, 4 metrics, and 1 semantic model;
- `GET /api/v1/lineage/fields/summary` returned `artifact_status=READY`, 2 field mappings, 18 annotated dbt columns, 4 metric bindings, 28 nodes, and 27 edges;
- the existing Phase 8.1 graph remained READY at 11 nodes and 10 edges;
- the mypy upstream-ID cleanup changed local variable naming only and preserved the field graph;
- final local validation passed Ruff, mypy across 57 source files, 80 pytest tests, npm audit with zero vulnerabilities, ESLint, and Vite production build.

## Phase 8.3 — Quality and Incident Lineage Overlay Foundation

**Status:** Complete. Live trust-overlay proof and final local validation are green.

Scope:

- preserve the Phase 8.1 asset graph and Phase 8.2 field graph without adding trust state to the persisted lineage model;
- project the latest dbt quality checks onto the dbt source/model assets and exact fields they protect;
- project the source-controlled Federal Funds Rate quality-contract selectors onto the mart asset and governed mart fields;
- project durable active quality incidents onto their affected asset and field nodes while keeping incident lifecycle ownership in the Phase 7 incident tables;
- expose a typed `GET /api/v1/lineage/trust/summary` read model with asset/field trust posture, check counts, contract coverage, and incident counts;
- extend the Lineage workbench with an explicit trust overlay that can be refreshed independently from structural lineage;
- keep Airflow/pipeline execution lineage and report/Power BI consumers outside this trust-overlay foundation.

Acceptance proof:

- with the current clean dbt evidence, the trust overlay reports `artifact_status=READY`, `evidence_trust_posture=TRUSTED`, and `contract_status=COMPLIANT`;
- all 14 dbt quality checks remain represented, with 14 passing and the 5 required quality-contract rules satisfied;
- exactly 4 structural asset nodes are quality-protected: the governed dbt source plus staging, intermediate, and mart models;
- exactly 9 field nodes receive direct quality evidence across source, staging, intermediate, and mart layers;
- the current clean incident register contributes zero active and zero blocking incidents without fabricating trust failures;
- synthetic lifecycle tests prove a blocking incident marks the owning mart asset and exact contract field `BLOCKED` while unrelated fields remain untouched;
- local validation remains green with 84 pytest tests plus Ruff, mypy, npm audit, ESLint, and Vite build.

Closure evidence:

- `GET /api/v1/lineage/trust/summary` returned `READY / TRUSTED / COMPLIANT`, 14/14 passing dbt checks, 5/5 satisfied contract rules, 4 protected assets, 9 protected fields, and zero active or blocking incidents;
- the Lineage workbench rendered the trust overlay over the existing Phase 8.1 and 8.2 structural graphs without adding persisted trust state;
- the mypy trust-overlay cleanup changed local variable naming only and preserved runtime behavior;
- final local validation passed Ruff, mypy across 58 source files, 84 pytest tests, npm audit with zero vulnerabilities, ESLint, and Vite production build.

## Phase 8.4 — Pipeline and Airflow Execution Lineage Foundation

**Status:** Complete. Live Airflow/Studio execution linkage and final local validation are green.

Scope:

- preserve the Phase 8.1 asset graph, Phase 8.2 field graph, and Phase 8.3 trust overlay while adding a separate runtime-lineage read model;
- use the latest replay-safe Studio `AIRFLOW:` pipeline run as the durable join key back to the owning Airflow DAG run;
- read Airflow DAG-run and task-instance state through REST API v2 only, never through the Airflow metadata database;
- project the Airflow DAG, DAG run, four Airflow tasks, Studio pipeline run, and four Studio step runs into one execution graph;
- anchor that runtime graph to the same `DFF` source and `FED_FUNDS_RATE_MART` curated target nodes already used by structural lineage;
- expose `GET /api/v1/lineage/runtime/summary` with execution counts, replay evidence, materialization evidence, and directed runtime edges;
- extend the Lineage workbench with a refreshable runtime execution surface;
- degrade to `PARTIAL` when Airflow is temporarily unavailable while retaining persisted Studio run and step evidence;
- keep report/Power BI consumer lineage outside this runtime foundation.

Acceptance proof:

- with the Phase 5 Airflow services running, the live runtime endpoint reports `runtime_status=READY` and `airflow_connection_status=CONNECTED`;
- the latest linked DAG run resolves from the persisted `AIRFLOW:<dag_run_id>` Studio run key rather than by timestamp guessing;
- the proof exposes 4 successful Airflow tasks and 4 successful Studio pipeline steps, with the Airflow `execute_studio_pipeline` task linked to the single replay-safe Studio run;
- the execution graph begins at the structural `DFF` source node and terminates at the structural `FED_FUNDS_RATE_MART` target node;
- materialization evidence preserves `materialization_executed=true`, target relation `mart.fed_funds_rate`, target row count, mutation posture, and replay count;
- a synthetic unavailable-Airflow test returns `PARTIAL` while retaining Studio execution evidence;
- local validation remains green with 88 pytest tests plus Ruff, mypy, npm audit, ESLint, and Vite build.

Closure evidence:

- `GET /api/v1/lineage/runtime/summary` returned `runtime_status=READY` and `airflow_connection_status=CONNECTED` for DAG run `scheduled__2026-08-13T00:00:00+00:00`;
- the linked Airflow execution reported 4/4 successful tasks and resolved exactly to Studio run key `AIRFLOW:scheduled__2026-08-13T00:00:00+00:00` with 4/4 successful Studio steps;
- materialization evidence reported `materialization_executed=true`, `data_mutation_applied=true`, target `mart.fed_funds_rate`, 26,340 target rows, and replay count 0;
- the runtime graph returned 14 nodes and 13 directed edges from the structural DFF source through Airflow and Studio execution to the curated target;
- the Lineage workbench rendered the runtime proof over the existing structural, field, and trust surfaces;
- final local validation passed Ruff, mypy across 59 source files, 88 pytest tests, npm audit with zero vulnerabilities, ESLint, and Vite production build.

## Phase 8.5 — Analytics Consumer Lineage and Impact Closure

**Status:** In progress. Consumer-contract resolution and metric-to-report impact are the active proof.

Scope:

- preserve the Phase 8.1 asset graph, Phase 8.2 field graph, Phase 8.3 trust overlay, and Phase 8.4 runtime graph without modifying their persisted authorities;
- add source-controlled analytics-consumer declarations that name the semantic model, governed metrics, and dimensions a downstream report requires;
- resolve those declarations against generated dbt semantic artifacts rather than introducing a second semantic metadata store;
- expose `GET /api/v1/lineage/consumers/summary` and `GET /api/v1/lineage/consumers/impact?metricName=...`;
- extend the Lineage workbench with governed metric → analytics consumer dependency evidence and metric-level downstream impact;
- declare the first Federal Funds Rate Overview report as a Power BI target with deployment status `DECLARED`, explicitly avoiding any claim that Power BI resources have already been provisioned;
- leave actual analytical product publication for Phase 9 and live Power BI workspace/report/refresh/deployment integration for Phase 10.

Acceptance proof:

- the consumer-lineage endpoint reports `consumer_status=READY` against READY dbt semantic artifacts;
- one source-controlled analytics consumer resolves to the `fed_funds_rate_daily` semantic model;
- all four declared governed metrics resolve with zero unresolved metric dependencies;
- the proof graph contains 5 nodes and 4 directed `CONSUMED_BY` edges: four governed metrics feeding one declared report consumer;
- selecting `average_federal_funds_rate` reports exactly one downstream consumer, `Federal Funds Rate Overview`;
- the declaration remains `deployment_status=DECLARED`, proving lineage without fabricating Power BI deployment state;
- the Lineage workbench renders the consumer dependency surface alongside the four completed Phase 8 evidence layers;
- local validation remains green with 92 pytest tests plus Ruff, mypy, npm audit, ESLint, and Vite build.

