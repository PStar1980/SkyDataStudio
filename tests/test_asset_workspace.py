import pytest
from skydata_contracts.skycommand import (
    AssetFreshnessList,
    AssetFreshnessResponse,
    CatalogueAssetList,
    CatalogueAssetResponse,
    CatalogueDomainList,
    CatalogueSourceList,
    IngestionRunList,
    QualityEventList,
    RejectionEventList,
    RevisionEventList,
)
from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.preview import (
    preview_asset_detail,
    preview_assets,
    preview_domains,
    preview_freshness,
    preview_freshness_detail,
    preview_quality_events,
    preview_rejection_events,
    preview_revision_events,
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

    async def get_asset(
        self,
        *,
        domain_code: str,
        asset_code: str,
    ) -> CatalogueAssetResponse:
        return preview_asset_detail(domain_code, asset_code)

    async def get_freshness(
        self,
        *,
        domain_code: str,
        asset_code: str,
    ) -> AssetFreshnessResponse:
        return preview_freshness_detail(domain_code, asset_code)

    async def list_quality_events(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        asset_code: str | None = None,
        ingestion_run_id: str | int | None = None,
        check_code: str | None = None,
        severity_code: str | None = None,
        blocking: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> QualityEventList:
        events = preview_quality_events()
        if asset_code:
            events.items = [item for item in events.items if item.asset_code == asset_code]
            events.total = len(events.items)
        return events

    async def list_revision_events(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        asset_code: str | None = None,
        ingestion_run_id: str | int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RevisionEventList:
        events = preview_revision_events()
        if asset_code:
            events.items = [item for item in events.items if item.asset_code == asset_code]
            events.total = len(events.items)
        return events

    async def list_rejection_events(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        asset_code: str | None = None,
        ingestion_run_id: str | int | None = None,
        check_code: str | None = None,
        severity_code: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RejectionEventList:
        events = preview_rejection_events()
        if asset_code:
            events.items = [item for item in events.items if item.asset_code == asset_code]
            events.total = len(events.items)
        return events


class FailingGateway(PreviewGateway):
    authenticated = False

    async def list_domains(self, *, active: bool = True) -> CatalogueDomainList:
        raise SkyCommandClientError("No bridge token.", category="CONFIGURATION")


class LegacyStatusGateway(PreviewGateway):
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
        freshness = preview_freshness()
        freshness.items[0].freshness.status_code = "FRESH"
        return freshness


async def test_asset_workspace_joins_catalogue_freshness_and_run_evidence() -> None:
    workspace = await build_asset_workspace(PreviewGateway(), preview_enabled=True)

    assert workspace.mode == "LIVE"
    assert workspace.connection.status == "CONNECTED"
    assert workspace.totals.assets == 6
    assert workspace.totals.sources == 3
    assert workspace.totals.current == 3
    assert workspace.totals.warning == 2
    assert workspace.totals.error == 1
    assert workspace.totals.inactive == 0
    assert workspace.totals.unknown == 0
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
        freshness_status="CURRENT",
        preview_enabled=True,
    )

    assert workspace.mode == "PREVIEW"
    assert workspace.totals.assets == 2
    assert {item.source_code for item in workspace.items} == {"FRED"}
    assert {item.freshness_status for item in workspace.items} == {"CURRENT"}


async def test_unknown_freshness_vocabulary_is_normalized() -> None:
    workspace = await build_asset_workspace(LegacyStatusGateway(), preview_enabled=True)

    dff = next(item for item in workspace.items if item.asset_code == "DFF")
    assert dff.freshness_status == "UNKNOWN"
    assert workspace.totals.current == 2
    assert workspace.totals.unknown == 1

