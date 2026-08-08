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
