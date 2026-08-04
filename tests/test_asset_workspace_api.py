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
    assert payload["totals"]["assets"] == 6
    assert payload["items"][0]["asset_code"]
