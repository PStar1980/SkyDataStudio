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
│   │       │       ├── health.py
│   │       │       ├── metadata.py
│   │       │       ├── pipeline_runs.py
│   │       │       ├── pipelines.py
│   │       │       ├── platform.py
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
│   │       │   └── pipeline.py
│   │       ├── schemas/
│   │       │   ├── __init__.py
│   │       │   ├── airflow.py
│   │       │   ├── assets.py
│   │       │   ├── execution.py
│   │       │   ├── metadata.py
│   │       │   ├── pipelines.py
│   │       │   └── platform.py
│   │       └── services/
│   │           ├── __init__.py
│   │           ├── asset_detail.py
│   │           ├── asset_workspace.py
│   │           ├── contract_compatibility.py
│   │           ├── metadata_registry.py
│   │           ├── pipeline_execution.py
│   │           └── pipeline_registry.py
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
│           │   ├── MetadataRegistry.jsx
│           │   ├── PipelineRuns.jsx
│           │   ├── Pipelines.jsx
│           │   ├── PlaceholderPage.jsx
│           │   ├── SourceMappings.jsx
│           │   └── StudioOverview.jsx
│           └── services/
│               └── api.js
├── contracts/
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
│   └── db/
│       └── migrations/
│           ├── 0001_metadata_registry.sql
│           ├── 0002_source_target_mapping.sql
│           ├── 0003_pipeline_definition.sql
│           └── 0004_pipeline_execution.sql
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
│   ├── test_health.py
│   ├── test_metadata_registry.py
│   ├── test_pipeline_registry.py
│   ├── test_platform.py
│   ├── test_quality_contracts.py
│   ├── test_skycommand_client.py
│   ├── test_skycommand_contracts.py
│   └── test_validation_environment.py
└── transformations/
    └── dbt/
        └── skydata_studio/
            ├── dbt_project.yml
            ├── profiles.yml.example
            ├── macros/
            │   └── .gitkeep
            ├── models/
            │   ├── intermediate/
            │   │   └── .gitkeep
            │   ├── marts/
            │   │   └── .gitkeep
            │   └── staging/
            │       ├── schema.yml
            │       ├── sources.yml
            │       └── stg_skycommand__ingestion_assets.sql
            ├── seeds/
            │   └── .gitkeep
            ├── snapshots/
            │   └── .gitkeep
            └── tests/
                └── .gitkeep
