import httpx
import pytest
from skydata_studio.integrations.skycommand.client import (
    SkyCommandClient,
    SkyCommandClientError,
)


@pytest.mark.anyio
async def test_skycommand_client_uses_internal_service_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-skycommand-internal-token"] == "bridge-secret"
        assert request.url.path == "/api/ingestion/catalogue/domains"
        assert request.url.params["active"] == "true"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "contractVersion": "data_catalogue.v1",
                "generatedAt": "2026-08-04T12:00:00Z",
                "items": [
                    {
                        "domainCode": "MACRO",
                        "domainName": "Macroeconomic Indicators",
                        "contractVersion": "data_catalogue.v1",
                        "active": True,
                    }
                ],
            },
        )

    client = SkyCommandClient(
        base_url="http://skycommand.local/api",
        token="bridge-secret",
        auth_mode="internal",
        transport=httpx.MockTransport(handler),
    )

    result = await client.list_domains()

    assert result.contract_version == "data_catalogue.v1"
    assert result.items[0].domain_code == "MACRO"


@pytest.mark.anyio
async def test_skycommand_client_surfaces_remote_permission_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"ok": False, "error": "Permission denied."})

    client = SkyCommandClient(
        base_url="http://skycommand.local/api",
        token="bridge-secret",
        auth_mode="internal",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SkyCommandClientError, match="Permission denied") as error:
        await client.list_assets()

    assert error.value.status_code == 403
    assert error.value.category == "HTTP"
