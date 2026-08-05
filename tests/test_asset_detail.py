import pytest
from skydata_contracts.skycommand import CatalogueAssetResponse
from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.services.asset_detail import build_asset_detail

from tests.test_asset_workspace import PreviewGateway

pytestmark = pytest.mark.anyio


class UnavailableDetailGateway(PreviewGateway):
    authenticated = False

    async def get_asset(
        self,
        *,
        domain_code: str,
        asset_code: str,
    ) -> CatalogueAssetResponse:
        raise SkyCommandClientError("Bridge unavailable.", category="CONNECTION")


async def test_asset_detail_joins_contract_and_quality_evidence() -> None:
    detail = await build_asset_detail(
        PreviewGateway(),
        domain_code="MACRO",
        asset_code="CA_CPI",
        preview_enabled=True,
    )

    assert detail.mode == "LIVE"
    assert detail.asset.asset_code == "CA_CPI"
    assert detail.freshness.freshness.status_code == "ERROR"
    assert detail.totals.quality_events == 1
    assert detail.totals.rejections == 1
    assert detail.totals.revisions == 0
    assert detail.compatibility.status == "COMPATIBLE"


async def test_asset_detail_preview_preserves_evidence_contracts() -> None:
    detail = await build_asset_detail(
        UnavailableDetailGateway(),
        domain_code="MACRO",
        asset_code="DFF",
        preview_enabled=True,
    )

    assert detail.mode == "PREVIEW"
    assert detail.connection.status == "PREVIEW"
    assert detail.asset.asset_code == "DFF"
    assert detail.totals.revisions == 1
    assert detail.compatibility.compatible == 5


class MissingAssetGateway(PreviewGateway):
    async def get_asset(
        self,
        *,
        domain_code: str,
        asset_code: str,
    ) -> CatalogueAssetResponse:
        raise SkyCommandClientError(
            "Data asset not found.",
            category="REMOTE_ERROR",
            status_code=404,
        )


async def test_asset_detail_does_not_mask_live_not_found_with_preview() -> None:
    with pytest.raises(SkyCommandClientError) as error:
        await build_asset_detail(
            MissingAssetGateway(),
            domain_code="MACRO",
            asset_code="DOES_NOT_EXIST",
            preview_enabled=True,
        )

    assert error.value.status_code == 404
