SkyDataStudio/
├── .editorconfig
├── .env.example
├── .gitignore
├── .python-version
├── Makefile
├── pyproject.toml
├── README.md
├── uv.lock
├── apps/
│   ├── api/
│   │   └── skydata_studio/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── router.py
│   │       │   └── routes/
│   │       │       ├── __init__.py
│   │       │       ├── airflow.py
│   │       │       ├── contracts.py
│   │       │       ├── dbt.py
│   │       │       ├── health.py
│   │       │       ├── metadata.py
│   │       │       ├── pipeline_runs.py
│   │       │       ├── pipelines.py
│   │       │       ├── platform.py
│   │       │       ├── quality.py
│   │       │       └── skycommand.py
│   │       ├── core/
│   │       │   ├── __init__.py
│   │       │   └── config.py
│   │       ├── db/
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   ├── bootstrap.py
│   │       │   └── session.py
│   │       ├── integrations/
│   │       │   ├── airflow/
│   │       │   │   ├── __init__.py
│   │       │   │   └── client.py
│   │       │   └── skycommand/
│   │       │       ├── __init__.py
│   │       │       ├── client.py
│   │       │       ├── dependencies.py
│   │       │       └── preview.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── metadata.py
│   │       │   ├── pipeline.py
│   │       │   └── quality.py
│   │       ├── schemas/
│   │       │   ├── __init__.py
│   │       │   ├── airflow.py
│   │       │   ├── assets.py
│   │       │   ├── dbt.py
│   │       │   ├── execution.py
│   │       │   ├── metadata.py
│   │       │   ├── pipelines.py
│   │       │   ├── platform.py
│   │       │   └── quality.py
│   │       └── services/
│   │           ├── __init__.py
│   │           ├── asset_detail.py
│   │           ├── asset_workspace.py
│   │           ├── contract_compatibility.py
│   │           ├── dbt_quality.py
│   │           ├── dbt_transformations.py
│   │           ├── metadata_registry.py
│   │           ├── pipeline_execution.py
│   │           ├── pipeline_registry.py
│   │           ├── quality_contracts.py
│   │           ├── quality_incidents.py
│   │           └── quality_reliability.py
│   └── web/
│       ├── eslint.config.js
│       ├── index.html
│       ├── package-lock.json
│       ├── package.json
│       ├── vite.config.js
│       └── src/
│           ├── App.jsx
│           ├── main.jsx
│           ├── styles.css
│           ├── components/
│           │   ├── BrandMark.jsx
│           │   ├── Sidebar.jsx
│           │   ├── StatusPill.jsx
│           │   └── Topbar.jsx
│           ├── pages/
│           │   ├── Airflow.jsx
│           │   ├── DataAssets.jsx
│           │   ├── DataContracts.jsx
│           │   ├── DataModels.jsx
│           │   ├── DataQuality.jsx
│           │   ├── MetadataRegistry.jsx
│           │   ├── PipelineRuns.jsx
│           │   ├── Pipelines.jsx
│           │   ├── PlaceholderPage.jsx
│           │   ├── QualityIncidents.jsx
│           │   ├── QualityReliability.jsx
│           │   ├── SchedulesBackfills.jsx
│           │   ├── SemanticLayer.jsx
│           │   ├── SourceMappings.jsx
│           │   ├── StudioOverview.jsx
│           │   └── Transformations.jsx
│           └── services/
│               └── api.js
├── contracts/
│   ├── quality/
│   │   ├── fed_funds_rate_daily.v1.json
│   │   └── README.md
│   └── skycommand/
│       └── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DESIGN_SYSTEM.md
│   ├── repository-map.txt
│   ├── ROADMAP.md
│   └── SkyData_RepoMap.md
├── infra/
│   ├── docker-compose.yml
│   ├── db/
│   │   └── migrations/
│   │       ├── 0001_metadata_registry.sql
│   │       ├── 0002_source_target_mapping.sql
│   │       ├── 0003_pipeline_definition.sql
│   │       ├── 0004_pipeline_execution.sql
│   │       ├── 0005_quality_incident.sql
│   │       └── 0006_quality_slo_observation.sql
│   └── dbt/
│       └── Dockerfile
├── orchestration/
│   └── airflow/
│       └── dags/
│           ├── fed_funds_rate_pipeline.py
│           └── studio_platform_smoke.py
├── packages/
│   └── contracts/
│       └── skydata_contracts/
│           ├── __init__.py
│           └── skycommand.py
├── scripts/
│   ├── bootstrap_metadata.py
│   ├── dbt.ps1
│   ├── generate_repo_map.py
│   ├── generate_repo_zip.py
│   ├── initialize_repo.ps1
│   ├── publish_github.ps1
│   └── validate.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_airflow_api.py
│   ├── test_airflow_client.py
│   ├── test_asset_detail.py
│   ├── test_asset_workspace_api.py
│   ├── test_asset_workspace.py
│   ├── test_contract_compatibility.py
│   ├── test_dbt_transformations.py
│   ├── test_health.py
│   ├── test_metadata_registry.py
│   ├── test_pipeline_registry.py
│   ├── test_platform.py
│   ├── test_quality_contracts.py
│   ├── test_quality_gate_contracts.py
│   ├── test_quality_incidents.py
│   ├── test_quality_reliability.py
│   ├── test_quality.py
│   ├── test_skycommand_client.py
│   ├── test_skycommand_contracts.py
│   └── test_validation_environment.py
└── transformations/
    └── dbt/
        └── skydata_studio/
            ├── .user.yml
            ├── dbt_project.yml
            ├── profiles.yml
            ├── profiles.yml.example
            ├── macros/
            │   ├── .gitkeep
            │   └── generate_schema_name.sql
            ├── models/
            │   ├── intermediate/
            │   │   ├── .gitkeep
            │   │   ├── int_fed_funds_rate_changes.sql
            │   │   └── schema.yml
            │   ├── marts/
            │   │   ├── fct_fed_funds_rate_daily.sql
            │   │   ├── schema.yml
            │   │   └── time_spine_daily.sql
            │   └── staging/
            │       ├── schema.yml
            │       ├── sources.yml
            │       ├── stg_fed_funds_rate.sql
            │       └── stg_skycommand__ingestion_assets.sql
            ├── seeds/
            │   └── .gitkeep
            ├── snapshots/
            │   └── .gitkeep
            ├── target/
            │   ├── graph_summary.json
            │   ├── graph.gpickle
            │   ├── manifest.json
            │   ├── osi_document.json
            │   ├── partial_parse.msgpack
            │   ├── run_results.json
            │   ├── semantic_manifest.json
            │   ├── compiled/
            │   │   └── skydata_studio/
            │   │       ├── models/
            │   │       │   ├── intermediate/
            │   │       │   │   ├── int_fed_funds_rate_changes.sql
            │   │       │   │   └── schema.yml/
            │   │       │   │       ├── not_null_int_fed_funds_rate_changes_observation_date.sql
            │   │       │   │       ├── not_null_int_fed_funds_rate_changes_rate.sql
            │   │       │   │       └── unique_int_fed_funds_rate_changes_observation_date.sql
            │   │       │   ├── marts/
            │   │       │   │   ├── fct_fed_funds_rate_daily.sql
            │   │       │   │   ├── time_spine_daily.sql
            │   │       │   │   └── schema.yml/
            │   │       │   │       ├── accepted_values_fct_fed_funds__ce738edf7a8c271de47c966afcab8ce8.sql
            │   │       │   │       ├── not_null_fct_fed_funds_rate_daily_observation_date.sql
            │   │       │   │       ├── not_null_fct_fed_funds_rate_daily_rate.sql
            │   │       │   │       └── unique_fct_fed_funds_rate_daily_observation_date.sql
            │   │       │   └── staging/
            │   │       │       ├── stg_fed_funds_rate.sql
            │   │       │       ├── schema.yml/
            │   │       │       │   ├── not_null_stg_fed_funds_rate_observation_date.sql
            │   │       │       │   ├── not_null_stg_fed_funds_rate_rate.sql
            │   │       │       │   └── unique_stg_fed_funds_rate_observation_date.sql
            │   │       │       └── sources.yml/
            │   │       │           ├── source_not_null_studio_curated_fed_funds_rate_observation_date.sql
            │   │       │           ├── source_not_null_studio_curated_fed_funds_rate_rate.sql
            │   │       │           └── source_unique_studio_curated_fed_funds_rate_observation_date.sql
            │   │       └── tests/
            │   │           └── assert_fed_funds_rate_reasonable.sql
            │   └── run/
            │       └── skydata_studio/
            │           ├── models/
            │           │   ├── intermediate/
            │           │   │   ├── int_fed_funds_rate_changes.sql
            │           │   │   └── schema.yml/
            │           │   │       ├── not_null_int_fed_funds_rate_changes_observation_date.sql
            │           │   │       ├── not_null_int_fed_funds_rate_changes_rate.sql
            │           │   │       └── unique_int_fed_funds_rate_changes_observation_date.sql
            │           │   ├── marts/
            │           │   │   ├── fct_fed_funds_rate_daily.sql
            │           │   │   ├── time_spine_daily.sql
            │           │   │   └── schema.yml/
            │           │   │       ├── accepted_values_fct_fed_funds__ce738edf7a8c271de47c966afcab8ce8.sql
            │           │   │       ├── not_null_fct_fed_funds_rate_daily_observation_date.sql
            │           │   │       ├── not_null_fct_fed_funds_rate_daily_rate.sql
            │           │   │       └── unique_fct_fed_funds_rate_daily_observation_date.sql
            │           │   └── staging/
            │           │       ├── stg_fed_funds_rate.sql
            │           │       ├── schema.yml/
            │           │       │   ├── not_null_stg_fed_funds_rate_observation_date.sql
            │           │       │   ├── not_null_stg_fed_funds_rate_rate.sql
            │           │       │   └── unique_stg_fed_funds_rate_observation_date.sql
            │           │       └── sources.yml/
            │           │           ├── source_not_null_studio_curated_fed_funds_rate_observation_date.sql
            │           │           ├── source_not_null_studio_curated_fed_funds_rate_rate.sql
            │           │           └── source_unique_studio_curated_fed_funds_rate_observation_date.sql
            │           └── tests/
            │               └── assert_fed_funds_rate_reasonable.sql
            └── tests/
                ├── .gitkeep
                └── assert_fed_funds_rate_reasonable.sql
