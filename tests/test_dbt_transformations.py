import json
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from skydata_studio.api.routes import dbt as dbt_route
from skydata_studio.db.session import get_session
from skydata_studio.main import app
from skydata_studio.schemas.dbt import DbtRelationSummary, DbtTransformationSummary
from skydata_studio.services.dbt_transformations import dbt_model_catalogue
from sqlalchemy.orm import Session

client = TestClient(app)


def test_dbt_summary_endpoint_projects_layered_model_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = DbtTransformationSummary(
        model_count=3,
        ready_model_count=3,
        test_count=14,
        layers_ready=3,
        layer_count=3,
        relations=[
            DbtRelationSummary(
                name="Federal Funds Rate curated source",
                layer="SOURCE",
                relation="mart.fed_funds_rate",
                materialization="SOURCE",
                description="Curated source.",
                status="READY",
                row_count=26335,
            ),
            DbtRelationSummary(
                name="stg_fed_funds_rate",
                layer="STAGING",
                relation="dbt_staging.stg_fed_funds_rate",
                materialization="VIEW",
                description="Staging model.",
                status="READY",
                row_count=26335,
            ),
            DbtRelationSummary(
                name="int_fed_funds_rate_changes",
                layer="INTERMEDIATE",
                relation="dbt_intermediate.int_fed_funds_rate_changes",
                materialization="VIEW",
                description="Intermediate model.",
                status="READY",
                row_count=26335,
            ),
            DbtRelationSummary(
                name="fct_fed_funds_rate_daily",
                layer="MART",
                relation="dbt_mart.fct_fed_funds_rate_daily",
                materialization="TABLE",
                description="Mart model.",
                status="READY",
                row_count=26335,
            ),
        ],
    )

    def fake_summary(session: Session) -> DbtTransformationSummary:
        del session
        return expected

    def override_session() -> Generator[Session, None, None]:
        with Session() as session:
            yield session

    monkeypatch.setattr(dbt_route, "dbt_transformation_summary", fake_summary)
    app.dependency_overrides[get_session] = override_session
    try:
        response = client.get("/api/v1/transformations/dbt/summary")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"] == "DOCKER"
    assert payload["ready_model_count"] == 3
    assert payload["layers_ready"] == 3
    assert payload["relations"][-1]["relation"] == "dbt_mart.fct_fed_funds_rate_daily"


def test_dbt_model_catalogue_projects_manifest_and_run_results(tmp_path: Path) -> None:
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    manifest = {
        "metadata": {"generated_at": "2026-08-11T15:47:34Z", "dbt_version": "1.12.0"},
        "sources": {
            "source.skydata_studio.studio_curated.fed_funds_rate": {
                "name": "fed_funds_rate",
                "resource_type": "source",
            }
        },
        "nodes": {
            "model.skydata_studio.stg_fed_funds_rate": {
                "resource_type": "model",
                "package_name": "skydata_studio",
                "name": "stg_fed_funds_rate",
                "schema": "dbt_staging",
                "alias": "stg_fed_funds_rate",
                "description": "Staging model",
                "original_file_path": "models/staging/stg_fed_funds_rate.sql",
                "tags": ["phase6", "staging"],
                "columns": {"observation_date": {"description": "Date"}},
                "config": {"enabled": True, "materialized": "view"},
                "depends_on": {
                    "nodes": ["source.skydata_studio.studio_curated.fed_funds_rate"]
                },
            },
            "model.skydata_studio.fct_fed_funds_rate_daily": {
                "resource_type": "model",
                "package_name": "skydata_studio",
                "name": "fct_fed_funds_rate_daily",
                "schema": "dbt_mart",
                "alias": "fct_fed_funds_rate_daily",
                "description": "Mart model",
                "original_file_path": "models/marts/fct_fed_funds_rate_daily.sql",
                "tags": ["phase6", "mart"],
                "columns": {"rate": {"description": "Rate"}},
                "config": {"enabled": True, "materialized": "table"},
                "depends_on": {"nodes": ["model.skydata_studio.stg_fed_funds_rate"]},
            },
            "test.skydata_studio.not_null_stg_fed_funds_rate": {
                "resource_type": "test",
                "package_name": "skydata_studio",
                "depends_on": {"nodes": ["model.skydata_studio.stg_fed_funds_rate"]},
            },
            "test.skydata_studio.unique_fct_fed_funds_rate_daily": {
                "resource_type": "test",
                "package_name": "skydata_studio",
                "depends_on": {"nodes": ["model.skydata_studio.fct_fed_funds_rate_daily"]},
            },
        },
    }
    run_results = {
        "results": [
            {"unique_id": "model.skydata_studio.stg_fed_funds_rate", "status": "success"},
            {
                "unique_id": "model.skydata_studio.fct_fed_funds_rate_daily",
                "status": "success",
            },
        ]
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (target_dir / "run_results.json").write_text(json.dumps(run_results), encoding="utf-8")

    summary = dbt_model_catalogue(target_dir)

    assert summary.artifact_status == "READY"
    assert summary.model_count == 2
    assert summary.ready_model_count == 2
    assert summary.source_count == 1
    assert summary.test_count == 2
    assert summary.models[0].layer == "STAGING"
    assert summary.models[0].upstream[0].resource_type == "SOURCE"
    assert summary.models[0].downstream[0].name == "fct_fed_funds_rate_daily"
    assert summary.models[1].materialization == "TABLE"
    assert summary.models[1].test_count == 1


def test_dbt_model_catalogue_returns_missing_when_manifest_is_absent(tmp_path: Path) -> None:
    summary = dbt_model_catalogue(tmp_path / "target")

    assert summary.artifact_status == "MISSING"
    assert summary.model_count == 0
    assert summary.models == []
