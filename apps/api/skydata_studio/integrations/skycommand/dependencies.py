from typing import Annotated, Literal, Protocol

from fastapi import Depends
from skydata_contracts.skycommand import (
    AssetFreshnessList,
    AssetFreshnessResponse,
    CatalogueAssetList,
    CatalogueAssetResponse,
    CatalogueDomainList,
    CatalogueSourceList,
    IngestionRunDetailResponse,
    IngestionRunList,
    QualityEventList,
    RejectionEventList,
    RevisionEventList,
    TimeSeriesObservationList,
)
from skydata_studio.core.config import Settings, get_settings
from skydata_studio.integrations.skycommand.client import SkyCommandClient


class SkyCommandGateway(Protocol):
    base_url: str

    @property
    def authenticated(self) -> bool: ...

    async def list_domains(self, *, active: bool = True) -> CatalogueDomainList: ...

    async def list_sources(
        self,
        *,
        domain_code: str | None = None,
    ) -> CatalogueSourceList: ...

    async def list_assets(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CatalogueAssetList: ...

    async def list_freshness(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        status_code: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AssetFreshnessList: ...

    async def list_runs(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> IngestionRunList: ...

    async def get_run(
        self,
        *,
        ingestion_run_id: str | int,
    ) -> IngestionRunDetailResponse: ...

    async def get_asset(
        self,
        *,
        domain_code: str,
        asset_code: str,
    ) -> CatalogueAssetResponse: ...

    async def get_freshness(
        self,
        *,
        domain_code: str,
        asset_code: str,
    ) -> AssetFreshnessResponse: ...

    async def list_asset_observations(
        self,
        *,
        domain_code: str,
        asset_code: str,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 250,
        offset: int = 0,
        sort_direction: Literal["ASC", "DESC"] = "ASC",
    ) -> TimeSeriesObservationList: ...

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
    ) -> QualityEventList: ...

    async def list_revision_events(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        asset_code: str | None = None,
        ingestion_run_id: str | int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RevisionEventList: ...

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
    ) -> RejectionEventList: ...


type SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_skycommand_gateway(settings: SettingsDependency) -> SkyCommandGateway:
    return SkyCommandClient(
        base_url=settings.skycommand_api_base_url,
        token=settings.skycommand_api_token,
        auth_mode=settings.skycommand_api_auth_mode,
        timeout_seconds=settings.skycommand_api_timeout_seconds,
    )


type SkyCommandGatewayDependency = Annotated[
    SkyCommandGateway,
    Depends(get_skycommand_gateway),
]
