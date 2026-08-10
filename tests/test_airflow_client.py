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
