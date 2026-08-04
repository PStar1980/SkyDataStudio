from fastapi.testclient import TestClient
from skydata_studio.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["application"] == "SkyData Studio API"
    assert payload["timestamp"]
