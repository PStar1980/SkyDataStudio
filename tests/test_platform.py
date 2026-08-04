from fastapi.testclient import TestClient
from skydata_studio.main import app

client = TestClient(app)


def test_platform_summary_exposes_product_boundary() -> None:
    response = client.get("/api/v1/platform/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["product"] == "SkyData Studio"
    assert payload["theme"] == "Aurora Foundry"
    assert "SkyCommand" in payload["boundary"]
    assert {item["code"] for item in payload["capabilities"]} >= {"AIRFLOW", "DBT"}


def test_skycommand_contract_catalogue_is_read_only() -> None:
    response = client.get("/api/v1/contracts/skycommand")

    assert response.status_code == 200
    payload = response.json()
    assert "ingestion_run_summary.v1" in {item["code"] for item in payload}
    assert all(item["access"] == "READ_ONLY" for item in payload)
