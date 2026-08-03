SkyDataStudio/
├── .editorconfig
├── .env.example
├── .gitignore
├── .python-version
├── Makefile
├── pyproject.toml
├── README.md
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
│   │       │       ├── contracts.py
│   │       │       ├── health.py
│   │       │       └── platform.py
│   │       ├── core/
│   │       │   ├── __init__.py
│   │       │   └── config.py
│   │       └── schemas/
│   │           ├── __init__.py
│   │           └── platform.py
│   └── web/
│       ├── eslint.config.js
│       ├── index.html
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
│           └── pages/
│               ├── PlaceholderPage.jsx
│               └── StudioOverview.jsx
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
│   └── docker-compose.yml
├── orchestration/
│   └── airflow/
│       └── dags/
│           └── studio_platform_smoke.py
├── packages/
│   └── contracts/
│       └── skydata_contracts/
│           ├── __init__.py
│           └── skycommand.py
├── scripts/
│   ├── generate_repo_map.py
│   ├── generate_repo_zip.py
│   ├── initialize_repo.ps1
│   ├── publish_github.ps1
│   └── validate.py
├── tests/
│   ├── test_health.py
│   ├── test_platform.py
│   └── test_skycommand_contracts.py
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
