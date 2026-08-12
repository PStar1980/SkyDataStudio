# SkyData Studio Architecture

## Bounded contexts

### SkyCommand

Owns source ingestion, source adapters, ingestion retries, ingestion quality evidence, the generic data catalogue, workflow automation, and operational controls.

### SkyData Studio

Owns post-ingestion transformations, pipeline specifications, Airflow DAGs, dbt models, downstream quality/reconciliation, lineage, analytical marts, semantic metadata, and reporting delivery.

### SkyWeb Analytics

Owns end-user analytical exploration, alerts, visual narratives, saved views, and product-specific experiences.

## Integration rules

1. Consume SkyCommand through versioned REST APIs or approved read-only views.
2. Never write into SkyCommand-owned schemas.
3. Never read or write the Airflow metadata database directly; use Airflow's stable `/api/v2` interface.
4. Treat dbt artifacts (`manifest.json`, `run_results.json`, `catalog.json`) as versioned evidence inputs.
5. Publish curated products through stable views, APIs, or export contracts.
6. Keep orchestration state and business/data evidence separate.

## Logical data layers

```text
RAW/TRUSTED     Produced by SkyCommand; source-shaped, traceable, minimally transformed
STAGING         Renamed, typed, standardized, deduplicated
INTERMEDIATE    Reusable business logic and joins
MART            Consumer-oriented facts, dimensions, aggregates
SEMANTIC        Governed metrics, measures, dimensions, and descriptions
DELIVERY        SkyWeb APIs/views, Power BI models, extracts, and reports
```

## Orchestration boundary

Temporal and Airflow coexist because they solve different problems:

- **Temporal:** durable application and operational workflows, approvals, tool execution, retries, long-running coordination.
- **Airflow:** batch-oriented data dependencies, schedules, backfills, data assets, task observability, and analytical pipeline runs.

A SkyCommand workflow may trigger or publish an Airflow asset event after successful ingestion. Airflow then coordinates downstream transformations. Operational remediation may call back into a SkyCommand workflow.


## Studio metadata registry

Phase 3 introduces a Studio-owned operational metadata database. It stores engineering representations of domains, systems, connection references, namespaces, assets, fields, ownership, classifications, tags, and dependencies. It does not copy source credentials or take ownership of SkyCommand ingestion state.

```text
SkyCommand data_asset.v1
        ↓ idempotent synchronization
metadata_domain ─ metadata_system ─ metadata_connection
        └──────── metadata_namespace ─ metadata_asset ─ metadata_field
                                           └────────── metadata_dependency
```

SkyCommand assets enter the registry as `RAW` assets. Studio-created products advance through `STAGING`, `INTERMEDIATE`, `MART`, `SEMANTIC`, and `REPORT` layers. The registry becomes the stable metadata boundary used by the pipeline workbench, dbt artifact ingestion, lineage, and analytics delivery.

### dbt semantic metadata boundary

Phase 6.3 keeps semantic authorship beside the dbt model that owns the analytical grain and supplies MetricFlow with a dedicated DAY-grain calendar time spine. The first contract flows `dbt_mart.fct_fed_funds_rate_daily → fed_funds_rate_daily semantic model → governed metrics → dbt artifacts → Studio Semantic Layer workbench`. SkyData Studio reads generated evidence; it does not copy dbt semantic definitions into Studio PostgreSQL. This phase establishes portable definitions and observability only, leaving hosted semantic-query execution and downstream BI integrations as later delivery boundaries.

### dbt quality evidence boundary

Phase 7.1 treats dbt test artifacts as the first downstream quality-evidence seam. Test definitions remain in dbt project YAML/SQL and execution remains inside the Dockerized dbt runtime. SkyData Studio joins `manifest.json` definitions to `run_results.json` outcomes and projects the latest trust posture through its API and Data Quality workbench.

```text
dbt test definitions
      │ manifest.json
      ├───────────────┐
      │               ▼
dbt build ─────── run_results.json
                      │
                      ▼
             Studio quality evidence
                      │
                      └── TRUSTED / DEGRADED / BLOCKED / PENDING
```

Phase 7.1 is intentionally observational and non-persistent. Phase 7.2 adds policy without adding a second test authority: a small source-controlled contract selects the dbt evidence that a downstream consumer requires.

### Quality contract gate boundary

```text
contracts/quality/*.json
        │ stable selectors
        ▼
Studio quality-contract evaluator ◀── Phase 7.1 latest dbt evidence
        │
        ├── COMPLIANT
        ├── DEGRADED
        ├── BLOCKED
        └── PENDING
```

The contract is versioned with application code and references target model, quality dimension, test kind, and column instead of dbt-generated test unique IDs. dbt still owns test definitions and execution. SkyCommand still owns its separate ingestion consumer contracts. The `/quality/contracts` workbench presents both boundaries together for visibility without collapsing their ownership. Phase 7.3 adds Studio-owned operational incident memory downstream of this policy seam; historical SLO calculation remains later work.


### Durable quality incident boundary

```text
dbt test evidence + source-controlled quality contract
                    │
                    ▼
            Phase 7.2 gate evaluator
                    │ rule outcome
       ┌────────────┼─────────────┐
       │            │             │
      PASS         WARN      BLOCK / MISSING
       │            │             │
       │            └──────┬──────┘
       │                   ▼
       │          quality_incident
       │                   │
       │          quality_incident_event
       │                   │
       │        OPEN → ACKNOWLEDGED
       │                   │
       └───────────────→ RESOLVED
                           │
                    failure returns
                           ▼
                        REOPENED
```

The incident key is stable at `contract_code + rule_code`, so repeated reconciliation does not create duplicates. A clean PASS does not create an incident. An active incident is resolved automatically when PASS evidence returns; a manually resolved incident is reopened if the same rule is still failing on the next reconciliation. This keeps policy, test execution, and operational memory as three distinct authorities.


## Product blueprint and mapping boundary

Phase 3.2 adds a design-time contract between registered source assets and intended targets. A mapping is metadata, not execution: it records how a pipeline *should* move and shape data before Phase 4 introduces a runnable pipeline engine.

```text
metadata_asset (source)
        │
        ├── metadata_mapping
        │       mapping type
        │       load strategy
        │       grain + business keys
        │       transformation sketch
        │
        ├── metadata_field_mapping ── target field contract
        │
        └── metadata_dependency ───── durable TRANSFORMS lineage edge
                                      │
                              metadata_asset (target)
```

Mapping registration may enrich the target asset schema, but it never executes SQL or mutates source data. This separation lets the Studio validate design intent, ownership, keys, and lineage before pipeline code or Airflow DAGs exist.

## Pipeline definition boundary

Phase 4.1 converts an accepted mapping blueprint into a versioned processing definition without running it. The pipeline catalogue owns design-time execution metadata while source/target authority remains in the metadata registry.

```text
pipeline_definition
        │ mapping_id → metadata_mapping
        └── pipeline_version (v1...vn)
                ├── pipeline_parameter
                └── pipeline_step
                        └── pipeline_step_dependency
```

The first execution contract is deliberately local-only. Steps can be typed as `SQL`, `PYTHON`, `VALIDATION`, `DBT`, or `PUBLISH` and carry retry, timeout, dependency, source/target, and optional SQL/script metadata. Persisting this graph before execution keeps Phase 4.2 free to focus on replay-safe runtime behavior and structured run evidence instead of mixing execution semantics with authoring concerns.


## Local pipeline execution boundary

Phase 4.2 executes the persisted graph without collapsing design metadata and runtime evidence into the same tables. Each logical execution owns one replay-safe `pipeline_run`, and each versioned step produces one `pipeline_step_run` result.

```text
pipeline_definition ── pipeline_version ── pipeline_step
        │                     │                 │
        └────────────── pipeline_run ───────────┘
                              │
                              └── pipeline_step_run
                                  status + attempt + timing
                                  structured result + error
```

The default replay key is deterministic across pipeline code, version, environment, and resolved parameters. Re-requesting the same logical work therefore returns the existing durable run instead of duplicating it; `FORCE_NEW` is the explicit escape hatch for diagnostic proof runs.

Phase 4.2 closed in non-mutating proof mode. `READ_SOURCE` proved the trusted source metadata boundary, transformation steps proved the governed mapping contract, `VALIDATION` proved target-schema compatibility, and `PUBLISH` recorded `ELIGIBLE_NOT_PUBLISHED` with `data_mutation_applied=false`.

## Curated materialization boundary

Phase 4.3 preserves the same versioned step graph and run-evidence model while replacing proof handlers with a governed data-plane execution path. Studio reads trusted observations from SkyCommand's portable `time_series_observations.v1` endpoint; it never queries SkyCommand implementation tables.

```text
SkyCommand observation contract
          │
          ▼
READ_SOURCE ── governed rows
          │
          ▼
TRANSFORM_TARGET ── registered field mappings + type coercion
          │
          ▼
VALIDATE_TARGET ── target schema + business-key checks
          │
          ▼
PUBLISH_TARGET ── idempotent MERGE
          │
          ▼
Studio PostgreSQL: mart.fed_funds_rate_mart
```

The materializer creates the target relation from registered Studio metadata when necessary and uses mapping business keys for matching. Existing rows with identical non-key values are counted as unchanged; changed values are updated; new business keys are inserted. Structured run evidence records read, transformed, inserted, updated, unchanged, rejected, published, and target-row counts.

Replay reuse remains intentionally different from a forced physical rerun. `REUSE` returns the existing durable execution and performs no second mutation. `FORCE_NEW` creates a distinct run and re-executes the same `MERGE`, which provides the idempotency proof: unchanged source data must not duplicate target rows. The replay-key canonical input also includes the execution-engine version so a pre-materialization Phase 4.2 run cannot be reused after the Phase 4.3 boundary is enabled.
