import pytest
from skydata_studio.services.contract_compatibility import (
    check_contract_compatibility,
    compatibility_items,
)

from tests.test_asset_workspace import FailingGateway, PreviewGateway

pytestmark = pytest.mark.anyio


def test_compatibility_items_detect_missing_and_incompatible_versions() -> None:
    items = compatibility_items(
        {
            "data_catalogue.v1": "data_catalogue.v1",
            "data_asset.v1": "data_asset.v2",
        }
    )

    statuses = {item.expected_version: item.status for item in items}
    assert statuses["data_catalogue.v1"] == "COMPATIBLE"
    assert statuses["data_asset.v1"] == "INCOMPATIBLE"
    assert statuses["asset_freshness.v1"] == "MISSING"


async def test_live_contract_compatibility_is_complete() -> None:
    response = await check_contract_compatibility(
        PreviewGateway(),
        preview_enabled=True,
    )

    assert response.mode == "LIVE"
    assert response.status == "COMPATIBLE"
    assert response.compatible == 5
    assert response.incompatible == 0
    assert response.missing == 0


async def test_contract_compatibility_falls_back_to_preview() -> None:
    response = await check_contract_compatibility(
        FailingGateway(),
        preview_enabled=True,
    )

    assert response.mode == "PREVIEW"
    assert response.status == "COMPATIBLE"
    assert response.connection.status == "PREVIEW"
