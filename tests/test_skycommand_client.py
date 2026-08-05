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


@pytest.mark.anyio
async def test_skycommand_client_reads_quality_evidence_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/ingestion/quality/events"
        assert request.url.params["assetCode"] == "DFF"
        assert request.url.params["blocking"] == "true"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "contractVersion": "ingestion_quality_evidence.v1",
                "generatedAt": "2026-08-05T12:00:00Z",
                "total": 1,
                "limit": 50,
                "offset": 0,
                "items": [
                    {
                        "eventType": "QUALITY",
                        "qualityEventId": "quality-1",
                        "domainCode": "MACRO",
                        "sourceCode": "FRED",
                        "assetCode": "DFF",
                        "checkCode": "UNEXPECTED_GAP",
                        "severityCode": "ERROR",
                        "blocking": True,
                        "message": "Unexpected gap detected.",
                        "createdAt": "2026-08-05T12:00:00Z",
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

    result = await client.list_quality_events(asset_code="DFF", blocking=True)

    assert result.total == 1
    assert result.items[0].blocking is True
