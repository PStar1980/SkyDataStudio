import pytest
from skydata_contracts.skycommand import (
    AssetFreshnessList,
    CatalogueAssetList,
    CatalogueDomainList,
    CatalogueSourceList,
    IngestionRunList,
)
from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.preview import (
    preview_assets,
    preview_domains,
    preview_freshness,
    preview_runs,
    preview_sources,
)
from skydata_studio.services.asset_workspace import build_asset_workspace

pytestmark = pytest.mark.anyio


class PreviewGateway:
    base_url = "http://skycommand.local/api"
    authenticated = True

    async def list_domains(self, *, active: bool = True) -> CatalogueDomainList:
        assert active is True
        return preview_domains()

    async def list_sources(
        self,
        *,
        domain_code: str | None = None,
    ) -> CatalogueSourceList:
        return preview_sources()

    async def list_assets(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CatalogueAssetList:
        return preview_assets()

    async def list_freshness(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        status_code: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AssetFreshnessList:
        return preview_freshness()

    async def list_runs(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> IngestionRunList:
        return preview_runs()


class FailingGateway(PreviewGateway):
    authenticated = False

    async def list_domains(self, *, active: bool = True) -> CatalogueDomainList:
        raise SkyCommandClientError("No bridge token.", category="CONFIGURATION")


async def test_asset_workspace_joins_catalogue_freshness_and_run_evidence() -> None:
    workspace = await build_asset_workspace(PreviewGateway(), preview_enabled=True)

    assert workspace.mode == "LIVE"
    assert workspace.connection.status == "CONNECTED"
    assert workspace.totals.assets == 6
    assert workspace.totals.sources == 3
    assert workspace.totals.stale == 1
    assert workspace.items[0].last_run_status == "SUCCESS"
    assert workspace.items[0].storage_relation


async def test_asset_workspace_falls_back_to_explicit_preview_mode() -> None:
    workspace = await build_asset_workspace(FailingGateway(), preview_enabled=True)

    assert workspace.mode == "PREVIEW"
    assert workspace.connection.status == "PREVIEW"
    assert "No bridge token" in workspace.connection.message
    assert workspace.totals.assets == 6


async def test_preview_mode_applies_workspace_filters() -> None:
    workspace = await build_asset_workspace(
        FailingGateway(),
        source_code="FRED",
        freshness_status="FRESH",
        preview_enabled=True,
    )

    assert workspace.mode == "PREVIEW"
    assert workspace.totals.assets == 2
    assert {item.source_code for item in workspace.items} == {"FRED"}
    assert {item.freshness_status for item in workspace.items} == {"FRESH"}
