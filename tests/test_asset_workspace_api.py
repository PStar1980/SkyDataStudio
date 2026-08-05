from fastapi.testclient import TestClient
from skydata_studio.integrations.skycommand.dependencies import get_skycommand_gateway
from skydata_studio.main import app

from tests.test_asset_workspace import PreviewGateway

client = TestClient(app)


def test_asset_workspace_endpoint_exposes_joined_contract_view() -> None:
    app.dependency_overrides[get_skycommand_gateway] = lambda: PreviewGateway()
    try:
        response = client.get("/api/v1/integrations/skycommand/workspace/assets")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "LIVE"
    assert payload["connection"]["status"] == "CONNECTED"
    assert payload["totals"] == {
        "assets": 6,
        "sources": 3,
        "current": 3,
        "warning": 2,
        "error": 1,
        "inactive": 0,
        "unknown": 0,
        "quality_issues": 0,
    }
    assert payload["items"][0]["asset_code"]
    assert {item["freshness_status"] for item in payload["items"]} == {
        "CURRENT",
        "ERROR",
        "WARNING",
    }


def test_contract_compatibility_endpoint_exposes_supported_boundary() -> None:
    app.dependency_overrides[get_skycommand_gateway] = lambda: PreviewGateway()
    try:
        response = client.get(
            "/api/v1/integrations/skycommand/contracts/compatibility"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPATIBLE"
    assert payload["compatible"] == 5


def test_asset_detail_endpoint_exposes_quality_evidence() -> None:
    app.dependency_overrides[get_skycommand_gateway] = lambda: PreviewGateway()
    try:
        response = client.get(
            "/api/v1/integrations/skycommand/workspace/assets/MACRO/CA_CPI"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"]["asset_code"] == "CA_CPI"
    assert payload["totals"]["quality_events"] == 1
    assert payload["totals"]["rejections"] == 1
    assert payload["compatibility"]["status"] == "COMPATIBLE"
