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


def test_airflow_ingestion_event_endpoints_emit_and_reuse_asset_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    from skydata_contracts.skycommand import (
        IngestionRunDetailItem,
        IngestionRunDetailResponse,
        IngestionRunList,
        IngestionRunRecord,
    )
    from skydata_studio.integrations.skycommand.client import SkyCommandClient
    from skydata_studio.schemas.airflow import AirflowAssetEventSummary, AirflowAssetSummary

    run = IngestionRunRecord(
        ingestionRunId=901,
        domainCode="MACRO",
        sourceCode="FRED",
        modeCode="INCREMENTAL",
        triggerCode="MANUAL",
        statusCode="SUCCEEDED",
        terminal=True,
        successLike=True,
        selectedAssets=["DFF"],
        startedAt=datetime(2026, 8, 10, 17, 0, tzinfo=UTC),
        completedAt=datetime(2026, 8, 10, 17, 1, tzinfo=UTC),
    )
    listing = IngestionRunList(
        contractVersion="ingestion_run_summary.v1",
        generatedAt=datetime(2026, 8, 10, 17, 2, tzinfo=UTC),
        total=1,
        items=[run],
    )
    detail = IngestionRunDetailResponse(
        contractVersion="ingestion_run_summary.v1",
        generatedAt=datetime(2026, 8, 10, 17, 2, tzinfo=UTC),
        run=run,
        items=[IngestionRunDetailItem(assetCode="DFF", outcomeCode="UNCHANGED")],
    )
    asset = AirflowAssetSummary(
        id=44,
        uri="x-skycommand://ingestion/macro/dff",
        name="skycommand_dff_ingestion_complete",
    )
    emitted_events: list[AirflowAssetEventSummary] = []

    async def fake_list_runs(
        self: SkyCommandClient,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> IngestionRunList:
        assert domain_code == "MACRO"
        assert source_code == "FRED"
        assert limit == 50
        assert offset == 0
        return listing

    async def fake_get_run(
        self: SkyCommandClient,
        *,
        ingestion_run_id: str | int,
    ) -> IngestionRunDetailResponse:
        assert str(ingestion_run_id) == "901"
        return detail

    def fake_asset_by_uri(self: AirflowClient, uri: str) -> AirflowAssetSummary | None:
        assert uri == "x-skycommand://ingestion/macro/dff"
        return asset

    def fake_asset_events(
        self: AirflowClient,
        asset_id: int,
        *,
        limit: int = 50,
    ) -> list[AirflowAssetEventSummary]:
        assert asset_id == 44
        assert limit == 50
        return list(emitted_events)

    def fake_create_asset_event(
        self: AirflowClient,
        asset_id: int,
        *,
        extra: dict[str, object],
    ) -> AirflowAssetEventSummary:
        assert asset_id == 44
        assert extra["event_type"] == "SKYCOMMAND_INGESTION_COMPLETE"
        assert extra["skycommand_ingestion_run_id"] == "901"
        event = AirflowAssetEventSummary(
            id=72,
            asset_id=44,
            uri=asset.uri,
            timestamp=datetime(2026, 8, 10, 17, 3, tzinfo=UTC),
            extra=extra,
            created_dag_run_ids=["asset__2026-08-10T17:03:00+00:00"],
        )
        emitted_events.append(event)
        return event

    monkeypatch.setattr(SkyCommandClient, "list_runs", fake_list_runs)
    monkeypatch.setattr(SkyCommandClient, "get_run", fake_get_run)
    monkeypatch.setattr(AirflowClient, "asset_by_uri", fake_asset_by_uri)
    monkeypatch.setattr(AirflowClient, "asset_events", fake_asset_events)
    monkeypatch.setattr(AirflowClient, "create_asset_event", fake_create_asset_event)

    preview_response = client.get(
        "/api/v1/integrations/airflow/dags/"
        "skydata_studio_fed_funds_rate_pipeline/ingestion-events/latest"
    )
    create_response = client.post(
        "/api/v1/integrations/airflow/dags/"
        "skydata_studio_fed_funds_rate_pipeline/ingestion-events",
        json={"ingestion_run_id": "901"},
    )
    reuse_response = client.post(
        "/api/v1/integrations/airflow/dags/"
        "skydata_studio_fed_funds_rate_pipeline/ingestion-events",
        json={"ingestion_run_id": "901"},
    )

    assert preview_response.status_code == 200
    assert preview_response.json()["eligible"] is True
    assert preview_response.json()["already_emitted"] is False
    assert preview_response.json()["ingestion_run"]["ingestion_run_id"] == "901"
    assert create_response.status_code == 201
    assert create_response.json()["reused"] is False
    assert create_response.json()["event"]["created_dag_run_ids"] == [
        "asset__2026-08-10T17:03:00+00:00"
    ]
    assert reuse_response.status_code == 201
    assert reuse_response.json()["reused"] is True
    assert len(emitted_events) == 1
