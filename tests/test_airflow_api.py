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
