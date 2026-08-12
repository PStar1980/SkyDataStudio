import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from skydata_studio.api.routes import quality as quality_route
from skydata_studio.main import app
from skydata_studio.schemas.quality import DbtQualitySummary
from skydata_studio.services.dbt_quality import dbt_quality_summary

client = TestClient(app)


def _write_manifest(target_dir: Path) -> None:
    manifest = {
        "metadata": {"generated_at": "2026-08-11T18:36:32Z", "dbt_version": "1.12.0"},
        "sources": {
            "source.skydata_studio.studio_curated.fed_funds_rate": {
                "resource_type": "source",
                "package_name": "skydata_studio",
                "name": "fed_funds_rate",
            }
        },
        "nodes": {
            "model.skydata_studio.fct_fed_funds_rate_daily": {
                "resource_type": "model",
                "package_name": "skydata_studio",
                "name": "fct_fed_funds_rate_daily",
                "schema": "dbt_mart",
                "original_file_path": "models/marts/fct_fed_funds_rate_daily.sql",
                "config": {"enabled": True},
            },
            "test.skydata_studio.source_not_null_rate": {
                "resource_type": "test",
                "package_name": "skydata_studio",
                "name": "source_not_null_rate",
                "column_name": "rate",
                "test_metadata": {"name": "not_null"},
                "attached_node": "source.skydata_studio.studio_curated.fed_funds_rate",
                "depends_on": {"nodes": ["source.skydata_studio.studio_curated.fed_funds_rate"]},
                "config": {"enabled": True, "severity": "ERROR"},
                "original_file_path": "models/staging/sources.yml",
            },
            "test.skydata_studio.unique_daily": {
                "resource_type": "test",
                "package_name": "skydata_studio",
                "name": "unique_daily",
                "column_name": "observation_date",
                "test_metadata": {"name": "unique"},
                "attached_node": "model.skydata_studio.fct_fed_funds_rate_daily",
                "depends_on": {"nodes": ["model.skydata_studio.fct_fed_funds_rate_daily"]},
                "config": {"enabled": True, "severity": "ERROR"},
                "original_file_path": "models/marts/schema.yml",
            },
            "test.skydata_studio.assert_rate_reasonable": {
                "resource_type": "test",
                "package_name": "skydata_studio",
                "name": "assert_rate_reasonable",
                "test_metadata": None,
                "depends_on": {"nodes": ["model.skydata_studio.fct_fed_funds_rate_daily"]},
                "config": {"enabled": True, "severity": "ERROR"},
                "original_file_path": "tests/assert_rate_reasonable.sql",
            },
        },
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_dbt_quality_summary_projects_test_evidence_and_trust_posture(tmp_path: Path) -> None:
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    _write_manifest(target_dir)
    run_results = {
        "metadata": {
            "generated_at": "2026-08-11T18:36:33Z",
            "dbt_version": "1.12.0",
            "invocation_id": "quality-proof",
        },
        "elapsed_time": 0.91,
        "args": {"invocation_command": "dbt build --profiles-dir ."},
        "results": [
            {
                "unique_id": "test.skydata_studio.source_not_null_rate",
                "status": "pass",
                "failures": 0,
                "execution_time": 0.08,
            },
            {
                "unique_id": "test.skydata_studio.unique_daily",
                "status": "pass",
                "failures": 0,
                "execution_time": 0.09,
            },
            {
                "unique_id": "test.skydata_studio.assert_rate_reasonable",
                "status": "pass",
                "failures": 0,
                "execution_time": 0.07,
            },
        ],
    }
    (target_dir / "run_results.json").write_text(json.dumps(run_results), encoding="utf-8")

    summary = dbt_quality_summary(target_dir)

    assert summary.artifact_status == "READY"
    assert summary.trust_posture == "TRUSTED"
    assert summary.test_count == 3
    assert summary.passed_count == 3
    assert summary.source_test_count == 1
    assert summary.model_test_count == 2
    assert {check.quality_dimension for check in summary.checks} == {
        "COMPLETENESS",
        "UNIQUENESS",
        "BUSINESS_RULE",
    }
    assert summary.checks[0].execution_time_ms is not None


def test_dbt_quality_summary_is_pending_without_run_results(tmp_path: Path) -> None:
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    _write_manifest(target_dir)

    summary = dbt_quality_summary(target_dir)

    assert summary.artifact_status == "PENDING"
    assert summary.trust_posture == "PENDING"
    assert summary.test_count == 3
    assert summary.unknown_count == 3
    assert all(check.status == "UNKNOWN" for check in summary.checks)


def test_quality_endpoint_projects_dbt_quality_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = DbtQualitySummary(
        artifact_status="READY",
        trust_posture="TRUSTED",
        generated_at="2026-08-11T18:36:33Z",
        dbt_version="1.12.0",
        invocation_id="quality-proof",
        invocation_command="dbt build --profiles-dir .",
        elapsed_time_ms=910.0,
        test_count=14,
        passed_count=14,
        warning_count=0,
        failed_count=0,
        error_count=0,
        skipped_count=0,
        unknown_count=0,
        source_test_count=3,
        model_test_count=11,
        checks=[],
    )

    monkeypatch.setattr(quality_route, "dbt_quality_summary", lambda: expected)

    response = client.get("/api/v1/quality/dbt/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["phase"].startswith("Phase 7.1")
    assert payload["trust_posture"] == "TRUSTED"
    assert payload["passed_count"] == 14
