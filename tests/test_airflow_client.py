import json

import httpx
from skydata_studio.integrations.airflow.client import AirflowClient


def test_airflow_client_reads_health_and_dag_catalogue() -> None:
    seen_authorization: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": "dev-token"})

        seen_authorization.append(request.headers.get("Authorization", ""))
        if request.url.path == "/api/v2/monitor/health":
            return httpx.Response(
                200,
                json={
                    "metadatabase": {"status": "healthy"},
                    "scheduler": {
                        "status": "healthy",
                        "latest_scheduler_heartbeat": "2026-08-09T19:00:00+00:00",
                    },
                    "dag_processor": {
                        "status": "healthy",
                        "latest_dag_processor_heartbeat": "2026-08-09T19:00:01+00:00",
                    },
                    "triggerer": {
                        "status": "healthy",
                        "latest_triggerer_heartbeat": "2026-08-09T19:00:02+00:00",
                    },
                },
            )
        if request.url.path == "/api/v2/dags":
            return httpx.Response(
                200,
                json={
                    "dags": [
                        {
                            "dag_id": "skydata_studio_platform_smoke",
                            "dag_display_name": "SkyData Studio Platform Smoke",
                            "description": "Validate the Studio Airflow authoring seam.",
                            "is_paused": False,
                            "is_stale": False,
                            "timetable_summary": "None",
                            "tags": [{"name": "skydata-studio"}],
                        }
                    ],
                    "total_entries": 1,
                },
            )
        return httpx.Response(404)

    client = AirflowClient(
        api_base_url="http://airflow.test/api/v2",
        auth_mode="simple-all-admins",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    summary = client.summary()

    assert summary.connection_status == "CONNECTED"
    assert summary.healthy_components == 4
    assert summary.component_count == 4
    assert summary.dag_count == 1
    assert summary.dags[0].dag_id == "skydata_studio_platform_smoke"
    assert summary.dags[0].tags == ["skydata-studio"]
    assert seen_authorization == ["Bearer dev-token", "Bearer dev-token"]


def test_airflow_client_reports_degraded_component_health() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": "dev-token"})
        if request.url.path == "/api/v2/monitor/health":
            return httpx.Response(
                200,
                json={
                    "metadatabase": {"status": "healthy"},
                    "scheduler": {"status": "unhealthy"},
                    "dag_processor": {"status": "healthy"},
                    "triggerer": {"status": "healthy"},
                },
            )
        if request.url.path == "/api/v2/dags":
            return httpx.Response(200, json={"dags": [], "total_entries": 0})
        return httpx.Response(404)

    client = AirflowClient(
        api_base_url="http://airflow.test/api/v2",
        auth_mode="simple-all-admins",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    summary = client.summary()

    assert summary.connection_status == "DEGRADED"
    assert summary.healthy_components == 3


def test_airflow_client_triggers_and_reads_dag_run_evidence() -> None:
    posted_payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": "dev-token"})
        if request.url.path == "/api/v2/dags/skydata_studio_fed_funds_rate_pipeline/dagRuns":
            if request.method == "POST":
                posted_payloads.append(json.loads(request.content.decode("utf-8")))
                return httpx.Response(
                    200,
                    json={
                        "dag_id": "skydata_studio_fed_funds_rate_pipeline",
                        "dag_run_id": posted_payloads[-1]["dag_run_id"],
                        "state": "queued",
                        "run_type": "manual",
                        "conf": posted_payloads[-1]["conf"],
                    },
                )
            return httpx.Response(
                200,
                json={
                    "dag_runs": [
                        {
                            "dag_id": "skydata_studio_fed_funds_rate_pipeline",
                            "dag_run_id": "skydata__proof",
                            "state": "success",
                            "run_type": "manual",
                            "start_date": "2026-08-10T15:00:00Z",
                            "end_date": "2026-08-10T15:00:03Z",
                            "conf": {
                                "pipeline_code": "FED_FUNDS_RATE_PIPELINE",
                                "run_date": "2026-08-10",
                            },
                        }
                    ],
                    "total_entries": 1,
                },
            )
        if request.url.path == (
            "/api/v2/dags/skydata_studio_fed_funds_rate_pipeline/"
            "dagRuns/skydata__proof"
        ):
            return httpx.Response(
                200,
                json={
                    "dag_id": "skydata_studio_fed_funds_rate_pipeline",
                    "dag_run_id": "skydata__proof",
                    "state": "success",
                    "run_type": "manual",
                    "conf": {"pipeline_code": "FED_FUNDS_RATE_PIPELINE"},
                },
            )
        if request.url.path == (
            "/api/v2/dags/skydata_studio_fed_funds_rate_pipeline/"
            "dagRuns/skydata__proof/taskInstances"
        ):
            return httpx.Response(
                200,
                json={
                    "task_instances": [
                        {
                            "task_id": "execute_studio_pipeline",
                            "task_display_name": "execute_studio_pipeline",
                            "state": "success",
                            "try_number": 1,
                            "map_index": -1,
                            "duration": 2.5,
                            "operator": "_PythonDecoratedOperator",
                        }
                    ],
                    "total_entries": 1,
                },
            )
        return httpx.Response(404)

    client = AirflowClient(
        api_base_url="http://airflow.test/api/v2",
        auth_mode="simple-all-admins",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    triggered = client.trigger_dag_run(
        "skydata_studio_fed_funds_rate_pipeline",
        conf={"pipeline_code": "FED_FUNDS_RATE_PIPELINE", "run_date": "2026-08-10"},
    )
    runs = client.dag_runs("skydata_studio_fed_funds_rate_pipeline")
    detail = client.dag_run_detail(
        "skydata_studio_fed_funds_rate_pipeline",
        "skydata__proof",
    )

    assert triggered.state == "QUEUED"
    assert str(posted_payloads[0]["dag_run_id"]).startswith("skydata__")
    assert runs.total == 1
    assert runs.items[0].state == "SUCCESS"
    assert detail.task_state_counts == {"SUCCESS": 1}
    assert detail.studio_run_key == "AIRFLOW:skydata__proof"


def test_airflow_client_creates_and_lists_backfills() -> None:
    from datetime import UTC, datetime

    posted_payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": "dev-token"})
        if request.url.path == "/api/v2/backfills":
            if request.method == "POST":
                posted_payloads.append(json.loads(request.content.decode("utf-8")))
                return httpx.Response(
                    200,
                    json={
                        "id": 11,
                        "dag_id": "skydata_studio_fed_funds_rate_pipeline",
                        "from_date": "2026-08-09T00:00:00Z",
                        "to_date": "2026-08-09T00:00:00Z",
                        "dag_run_conf": posted_payloads[-1]["dag_run_conf"],
                        "is_paused": False,
                        "reprocess_behavior": "none",
                        "max_active_runs": 1,
                        "run_backwards": False,
                        "created_at": "2026-08-10T20:00:00Z",
                    },
                )
            assert request.url.params["dag_id"] == "skydata_studio_fed_funds_rate_pipeline"
            return httpx.Response(
                200,
                json={
                    "backfills": [
                        {
                            "id": 11,
                            "dag_id": "skydata_studio_fed_funds_rate_pipeline",
                            "from_date": "2026-08-09T00:00:00Z",
                            "to_date": "2026-08-09T00:00:00Z",
                            "is_paused": False,
                            "reprocess_behavior": "none",
                            "max_active_runs": 1,
                            "run_backwards": False,
                            "created_at": "2026-08-10T20:00:00Z",
                        }
                    ],
                    "total_entries": 1,
                },
            )
        return httpx.Response(404)

    client = AirflowClient(
        api_base_url="http://airflow.test/api/v2",
        auth_mode="simple-all-admins",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    created = client.create_backfill(
        "skydata_studio_fed_funds_rate_pipeline",
        from_date=datetime(2026, 8, 9, tzinfo=UTC),
        to_date=datetime(2026, 8, 9, tzinfo=UTC),
        reprocess_behavior="none",
        max_active_runs=1,
        run_backwards=False,
        conf={
            "pipeline_code": "FED_FUNDS_RATE_PIPELINE",
            "trigger_mode": "BACKFILL",
        },
    )
    backfills = client.backfills("skydata_studio_fed_funds_rate_pipeline")

    assert created.id == 11
    assert backfills.total == 1
    assert backfills.items[0].reprocess_behavior == "none"
    assert posted_payloads[0]["max_active_runs"] == 1
    assert posted_payloads[0]["dag_run_conf"] == {
        "pipeline_code": "FED_FUNDS_RATE_PIPELINE",
        "trigger_mode": "BACKFILL",
    }


def test_airflow_client_reads_and_emits_asset_events() -> None:
    posted_payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": "dev-token"})
        if request.url.path == "/api/v2/assets":
            assert request.url.params["uri_pattern"] == "x-skycommand://ingestion/macro/dff"
            return httpx.Response(
                200,
                json={
                    "assets": [
                        {
                            "id": 44,
                            "uri": "x-skycommand://ingestion/macro/dff",
                            "name": "skycommand_dff_ingestion_complete",
                            "group": "asset",
                        }
                    ],
                    "total_entries": 1,
                },
            )
        if request.url.path == "/api/v2/assets/events":
            if request.method == "POST":
                posted_payloads.append(json.loads(request.content.decode("utf-8")))
                return httpx.Response(
                    200,
                    json={
                        "id": 72,
                        "asset_id": 44,
                        "uri": "x-skycommand://ingestion/macro/dff",
                        "extra": posted_payloads[-1]["extra"],
                        "created_dagruns": [
                            {"run_id": "asset__2026-08-10T17:03:00+00:00"}
                        ],
                        "timestamp": "2026-08-10T17:03:00Z",
                    },
                )
            assert request.url.params["asset_id"] == "44"
            return httpx.Response(
                200,
                json={
                    "asset_events": [
                        {
                            "id": 71,
                            "asset_id": 44,
                            "uri": "x-skycommand://ingestion/macro/dff",
                            "extra": {"skycommand_ingestion_run_id": "900"},
                            "created_dagruns": [],
                            "timestamp": "2026-08-10T16:00:00Z",
                        }
                    ],
                    "total_entries": 1,
                },
            )
        return httpx.Response(404)

    client = AirflowClient(
        api_base_url="http://airflow.test/api/v2",
        auth_mode="simple-all-admins",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    asset = client.asset_by_uri("x-skycommand://ingestion/macro/dff")
    assert asset is not None
    events = client.asset_events(asset.id)
    created = client.create_asset_event(
        asset.id,
        extra={
            "event_type": "SKYCOMMAND_INGESTION_COMPLETE",
            "skycommand_ingestion_run_id": "901",
        },
    )

    assert asset.id == 44
    assert events[0].extra["skycommand_ingestion_run_id"] == "900"
    assert created.created_dag_run_ids == ["asset__2026-08-10T17:03:00+00:00"]
    assert posted_payloads[0]["asset_id"] == 44
