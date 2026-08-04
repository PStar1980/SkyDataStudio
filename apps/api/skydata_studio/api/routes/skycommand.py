from fastapi import APIRouter, Depends, HTTPException, Query
from skydata_contracts.skycommand import (
    AssetFreshnessList,
    CatalogueAssetList,
    CatalogueDomainList,
    CatalogueSourceList,
    IngestionRunList,
)

from skydata_studio.core.config import Settings, get_settings
from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.dependencies import (
    SkyCommandGateway,
    get_skycommand_gateway,
)
from skydata_studio.schemas.assets import (
    AssetWorkspaceResponse,
    SkyCommandIntegrationHealth,
)
from skydata_studio.services.asset_workspace import (
    build_asset_workspace,
    check_skycommand_health,
)

router = APIRouter()


@router.get("/health", response_model=SkyCommandIntegrationHealth)
async def skycommand_health(
    gateway: SkyCommandGateway = Depends(get_skycommand_gateway),
    settings: Settings = Depends(get_settings),
) -> SkyCommandIntegrationHealth:
    return await check_skycommand_health(
        gateway,
        preview_enabled=settings.skycommand_offline_preview_enabled,
    )


@router.get("/domains", response_model=CatalogueDomainList)
async def skycommand_domains(
    gateway: SkyCommandGateway = Depends(get_skycommand_gateway),
) -> CatalogueDomainList:
    try:
        return await gateway.list_domains(active=True)
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/sources", response_model=CatalogueSourceList)
async def skycommand_sources(
    domain_code: str | None = Query(default=None, alias="domainCode"),
    gateway: SkyCommandGateway = Depends(get_skycommand_gateway),
) -> CatalogueSourceList:
    try:
        return await gateway.list_sources(domain_code=domain_code)
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/assets", response_model=CatalogueAssetList)
async def skycommand_assets(
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    gateway: SkyCommandGateway = Depends(get_skycommand_gateway),
) -> CatalogueAssetList:
    try:
        return await gateway.list_assets(
            domain_code=domain_code,
            source_code=source_code,
            search=search,
            limit=limit,
            offset=offset,
        )
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/freshness", response_model=AssetFreshnessList)
async def skycommand_freshness(
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    status_code: str | None = Query(default=None, alias="statusCode"),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    gateway: SkyCommandGateway = Depends(get_skycommand_gateway),
) -> AssetFreshnessList:
    try:
        return await gateway.list_freshness(
            domain_code=domain_code,
            source_code=source_code,
            status_code=status_code,
            search=search,
            limit=limit,
            offset=offset,
        )
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/runs", response_model=IngestionRunList)
async def skycommand_runs(
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    limit: int = Query(default=25, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    gateway: SkyCommandGateway = Depends(get_skycommand_gateway),
) -> IngestionRunList:
    try:
        return await gateway.list_runs(
            domain_code=domain_code,
            source_code=source_code,
            limit=limit,
            offset=offset,
        )
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/workspace/assets", response_model=AssetWorkspaceResponse)
async def asset_workspace(
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    freshness_status: str | None = Query(default=None, alias="freshnessStatus"),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    gateway: SkyCommandGateway = Depends(get_skycommand_gateway),
    settings: Settings = Depends(get_settings),
) -> AssetWorkspaceResponse:
    try:
        return await build_asset_workspace(
            gateway,
            domain_code=domain_code,
            source_code=source_code,
            freshness_status=freshness_status,
            search=search,
            limit=limit,
            offset=offset,
            preview_enabled=settings.skycommand_offline_preview_enabled,
        )
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
