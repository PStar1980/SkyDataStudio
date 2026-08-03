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
