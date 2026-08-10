import pytest
from fastapi.testclient import TestClient
from skydata_studio.integrations.airflow.client import AirflowClient
from skydata_studio.main import app
from skydata_studio.schemas.airflow import AirflowIntegrationSummary

client = TestClient(app)


def test_airflow_summary_endpoint_projects_client_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = AirflowIntegrationSummary(
        connection_status="CONNECTED",
        api_version="v2",
        api_base_url="http://localhost:8080/api/v2",
        ui_url="http://localhost:8080",
        auth_mode="simple-all-admins",
        dag_count=1,
        healthy_components=4,
        component_count=4,
        components=[],
        dags=[],
    )
    def fake_summary(self: AirflowClient) -> AirflowIntegrationSummary:
        return expected

    monkeypatch.setattr(AirflowClient, "summary", fake_summary)

    response = client.get("/api/v1/integrations/airflow/summary")

    assert response.status_code == 200
    assert response.json()["connection_status"] == "CONNECTED"
    assert response.json()["api_version"] == "v2"


def test_airflow_dag_run_endpoints_project_public_api_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from skydata_studio.schemas.airflow import (
        AirflowDagRunDetail,
        AirflowDagRunList,
        AirflowDagRunSummary,
        AirflowTaskInstanceSummary,
    )

    run = AirflowDagRunSummary(
        dag_id="skydata_studio_fed_funds_rate_pipeline",
        dag_run_id="skydata__proof",
        state="SUCCESS",
        conf={"pipeline_code": "FED_FUNDS_RATE_PIPELINE", "run_date": "2026-08-10"},
    )

    def fake_runs(
        self: AirflowClient,
        dag_id: str,
        *,
        limit: int = 20,
    ) -> AirflowDagRunList:
        assert dag_id == "skydata_studio_fed_funds_rate_pipeline"
        assert limit == 20
        return AirflowDagRunList(dag_id=dag_id, total=1, items=[run])

    def fake_detail(
        self: AirflowClient,
        dag_id: str,
        dag_run_id: str,
    ) -> AirflowDagRunDetail:
        assert dag_id == "skydata_studio_fed_funds_rate_pipeline"
        assert dag_run_id == "skydata__proof"
        return AirflowDagRunDetail(
            run=run,
            tasks=[
                AirflowTaskInstanceSummary(
                    task_id="publish_batch_evidence",
                    task_display_name="publish_batch_evidence",
                    state="SUCCESS",
                    try_number=1,
                )
            ],
            task_state_counts={"SUCCESS": 1},
            studio_run_key="AIRFLOW:skydata__proof",
        )

    def fake_trigger(
        self: AirflowClient,
        dag_id: str,
        *,
        conf: dict[str, object],
    ) -> AirflowDagRunSummary:
        assert dag_id == "skydata_studio_fed_funds_rate_pipeline"
        assert conf["pipeline_code"] == "FED_FUNDS_RATE_PIPELINE"
        return run

    monkeypatch.setattr(AirflowClient, "dag_runs", fake_runs)
    monkeypatch.setattr(AirflowClient, "dag_run_detail", fake_detail)
    monkeypatch.setattr(AirflowClient, "trigger_dag_run", fake_trigger)

    list_response = client.get(
        "/api/v1/integrations/airflow/dags/skydata_studio_fed_funds_rate_pipeline/runs"
    )
    detail_response = client.get(
        "/api/v1/integrations/airflow/dags/"
        "skydata_studio_fed_funds_rate_pipeline/runs/skydata__proof"
    )
    trigger_response = client.post(
        "/api/v1/integrations/airflow/dags/skydata_studio_fed_funds_rate_pipeline/runs",
        json={"pipeline_code": "FED_FUNDS_RATE_PIPELINE", "run_date": "2026-08-10"},
    )

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["state"] == "SUCCESS"
    assert detail_response.status_code == 200
    assert detail_response.json()["studio_run_key"] == "AIRFLOW:skydata__proof"
    assert trigger_response.status_code == 201
    assert trigger_response.json()["run"]["dag_run_id"] == "skydata__proof"


def test_airflow_backfill_endpoints_apply_controlled_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    from skydata_studio.schemas.airflow import AirflowBackfillList, AirflowBackfillSummary

    backfill = AirflowBackfillSummary(
        id=7,
        dag_id="skydata_studio_fed_funds_rate_pipeline",
        from_date=datetime(2026, 8, 9, tzinfo=UTC),
        to_date=datetime(2026, 8, 9, tzinfo=UTC),
        is_paused=False,
        reprocess_behavior="none",
        max_active_runs=1,
        run_backwards=False,
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
    )

    def fake_backfills(
        self: AirflowClient,
        dag_id: str,
        *,
        limit: int = 20,
    ) -> AirflowBackfillList:
        assert dag_id == "skydata_studio_fed_funds_rate_pipeline"
        assert limit == 20
        return AirflowBackfillList(dag_id=dag_id, total=1, items=[backfill])

    def fake_create_backfill(
        self: AirflowClient,
        dag_id: str,
        *,
        from_date: datetime,
        to_date: datetime,
        reprocess_behavior: str,
        max_active_runs: int,
        run_backwards: bool,
        conf: dict[str, object],
    ) -> AirflowBackfillSummary:
        assert dag_id == "skydata_studio_fed_funds_rate_pipeline"
        assert from_date == datetime(2026, 8, 9, tzinfo=UTC)
        assert to_date == datetime(2026, 8, 9, tzinfo=UTC)
        assert reprocess_behavior == "none"
        assert max_active_runs == 1
        assert run_backwards is False
        assert conf == {
            "pipeline_code": "FED_FUNDS_RATE_PIPELINE",
            "trigger_mode": "BACKFILL",
        }
        return backfill

    monkeypatch.setattr(AirflowClient, "backfills", fake_backfills)
    monkeypatch.setattr(AirflowClient, "create_backfill", fake_create_backfill)

    list_response = client.get(
        "/api/v1/integrations/airflow/dags/"
        "skydata_studio_fed_funds_rate_pipeline/backfills"
    )
    create_response = client.post(
        "/api/v1/integrations/airflow/dags/"
        "skydata_studio_fed_funds_rate_pipeline/backfills",
        json={
            "pipeline_code": "FED_FUNDS_RATE_PIPELINE",
            "from_date": "2026-08-09",
            "to_date": "2026-08-09",
            "reprocess_behavior": "none",
            "max_active_runs": 1,
            "run_backwards": False,
        },
    )
    oversized_response = client.post(
        "/api/v1/integrations/airflow/dags/"
        "skydata_studio_fed_funds_rate_pipeline/backfills",
        json={
            "from_date": "2026-08-01",
            "to_date": "2026-08-08",
        },
    )

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == 7
    assert create_response.status_code == 201
    assert create_response.json()["backfill"]["reprocess_behavior"] == "none"
    assert oversized_response.status_code == 422
