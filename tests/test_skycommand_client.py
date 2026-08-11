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


@pytest.mark.anyio
async def test_skycommand_client_reads_portable_time_series_observations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/ingestion/catalogue/assets/MACRO/DFF/observations"
        assert request.url.params["dateTo"] == "2026-08-08"
        assert request.url.params["limit"] == "5000"
        assert request.url.params["offset"] == "0"
        assert request.url.params["sortDirection"] == "ASC"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "generatedAt": "2026-08-08T12:00:00Z",
                "contractVersion": "time_series_observations.v1",
                "asset": {
                    "domainCode": "MACRO",
                    "domainName": "Macroeconomic Data",
                    "assetCode": "DFF",
                    "assetName": "Effective Federal Funds Rate",
                    "assetKindCode": "TIME_SERIES",
                    "frequencyCode": "DAILY",
                    "unitCode": "PERCENT",
                    "contractVersion": "data_asset.v1",
                },
                "total": 2,
                "limit": 5000,
                "offset": 0,
                "sortDirection": "ASC",
                "operator": "IDENTITY",
                "items": [
                    {"observationDate": "2026-08-07", "value": 4.33},
                    {"observationDate": "2026-08-08", "value": 4.33},
                ],
            },
        )

    client = SkyCommandClient(
        base_url="http://skycommand.local/api",
        token="bridge-secret",
        auth_mode="internal",
        transport=httpx.MockTransport(handler),
    )

    result = await client.list_asset_observations(
        domain_code="MACRO",
        asset_code="DFF",
        date_to="2026-08-08",
        limit=5000,
    )

    assert result.contract_version == "time_series_observations.v1"
    assert result.total == 2
    assert result.items[-1].observation_date.isoformat() == "2026-08-08"


@pytest.mark.anyio
async def test_skycommand_client_reads_ingestion_run_detail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/ingestion/runs/901"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "contractVersion": "ingestion_run_summary.v1",
                "generatedAt": "2026-08-10T17:02:00Z",
                "run": {
                    "ingestionRunId": 901,
                    "domainCode": "MACRO",
                    "sourceCode": "FRED",
                    "modeCode": "INCREMENTAL",
                    "triggerCode": "MANUAL",
                    "statusCode": "SUCCEEDED",
                    "terminal": True,
                    "successLike": True,
                    "selectedAssets": ["DFF"],
                    "startedAt": "2026-08-10T17:00:00Z",
                    "completedAt": "2026-08-10T17:01:00Z",
                },
                "items": [
                    {
                        "assetCode": "DFF",
                        "outcomeCode": "UNCHANGED",
                        "rows": {"unchanged": 1},
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

    detail = await client.get_run(ingestion_run_id=901)

    assert detail.run.ingestion_run_id == 901
    assert detail.run.success_like is True
    assert detail.items[0].asset_code == "DFF"
