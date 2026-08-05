from fastapi import APIRouter, HTTPException, Query
from skydata_contracts.skycommand import (
    AssetFreshnessList,
    CatalogueAssetList,
    CatalogueDomainList,
    CatalogueSourceList,
    IngestionRunList,
    QualityEventList,
    RejectionEventList,
    RevisionEventList,
)

from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.dependencies import (
    SettingsDependency,
    SkyCommandGatewayDependency,
)
from skydata_studio.schemas.assets import (
    AssetDetailResponse,
    AssetWorkspaceResponse,
    ContractCompatibilityResponse,
    SkyCommandIntegrationHealth,
)
from skydata_studio.services.asset_detail import build_asset_detail
from skydata_studio.services.asset_workspace import (
    build_asset_workspace,
    check_skycommand_health,
)
from skydata_studio.services.contract_compatibility import (
    check_contract_compatibility,
)

router = APIRouter()


@router.get("/health", response_model=SkyCommandIntegrationHealth)
async def skycommand_health(
    gateway: SkyCommandGatewayDependency,
    settings: SettingsDependency,
) -> SkyCommandIntegrationHealth:
    return await check_skycommand_health(
        gateway,
        preview_enabled=settings.skycommand_offline_preview_enabled,
    )


@router.get("/domains", response_model=CatalogueDomainList)
async def skycommand_domains(
    gateway: SkyCommandGatewayDependency,
) -> CatalogueDomainList:
    try:
        return await gateway.list_domains(active=True)
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/sources", response_model=CatalogueSourceList)
async def skycommand_sources(
    gateway: SkyCommandGatewayDependency,
    domain_code: str | None = Query(default=None, alias="domainCode"),
) -> CatalogueSourceList:
    try:
        return await gateway.list_sources(domain_code=domain_code)
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/assets", response_model=CatalogueAssetList)
async def skycommand_assets(
    gateway: SkyCommandGatewayDependency,
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
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
    gateway: SkyCommandGatewayDependency,
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    status_code: str | None = Query(default=None, alias="statusCode"),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
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
    gateway: SkyCommandGatewayDependency,
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    limit: int = Query(default=25, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
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
    gateway: SkyCommandGatewayDependency,
    settings: SettingsDependency,
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    freshness_status: str | None = Query(default=None, alias="freshnessStatus"),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
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


@router.get(
    "/contracts/compatibility",
    response_model=ContractCompatibilityResponse,
)
async def skycommand_contract_compatibility(
    gateway: SkyCommandGatewayDependency,
    settings: SettingsDependency,
) -> ContractCompatibilityResponse:
    return await check_contract_compatibility(
        gateway,
        preview_enabled=settings.skycommand_offline_preview_enabled,
    )


@router.get("/quality/events", response_model=QualityEventList)
async def skycommand_quality_events(
    gateway: SkyCommandGatewayDependency,
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    asset_code: str | None = Query(default=None, alias="assetCode"),
    ingestion_run_id: str | None = Query(default=None, alias="ingestionRunId"),
    check_code: str | None = Query(default=None, alias="checkCode"),
    severity_code: str | None = Query(default=None, alias="severityCode"),
    blocking: bool | None = None,
    limit: int = Query(default=50, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
) -> QualityEventList:
    try:
        return await gateway.list_quality_events(
            domain_code=domain_code,
            source_code=source_code,
            asset_code=asset_code,
            ingestion_run_id=ingestion_run_id,
            check_code=check_code,
            severity_code=severity_code,
            blocking=blocking,
            limit=limit,
            offset=offset,
        )
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/quality/revisions", response_model=RevisionEventList)
async def skycommand_revision_events(
    gateway: SkyCommandGatewayDependency,
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    asset_code: str | None = Query(default=None, alias="assetCode"),
    ingestion_run_id: str | None = Query(default=None, alias="ingestionRunId"),
    limit: int = Query(default=50, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
) -> RevisionEventList:
    try:
        return await gateway.list_revision_events(
            domain_code=domain_code,
            source_code=source_code,
            asset_code=asset_code,
            ingestion_run_id=ingestion_run_id,
            limit=limit,
            offset=offset,
        )
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/quality/rejections", response_model=RejectionEventList)
async def skycommand_rejection_events(
    gateway: SkyCommandGatewayDependency,
    domain_code: str | None = Query(default=None, alias="domainCode"),
    source_code: str | None = Query(default=None, alias="sourceCode"),
    asset_code: str | None = Query(default=None, alias="assetCode"),
    ingestion_run_id: str | None = Query(default=None, alias="ingestionRunId"),
    check_code: str | None = Query(default=None, alias="checkCode"),
    severity_code: str | None = Query(default=None, alias="severityCode"),
    limit: int = Query(default=50, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
) -> RejectionEventList:
    try:
        return await gateway.list_rejection_events(
            domain_code=domain_code,
            source_code=source_code,
            asset_code=asset_code,
            ingestion_run_id=ingestion_run_id,
            check_code=check_code,
            severity_code=severity_code,
            limit=limit,
            offset=offset,
        )
    except SkyCommandClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get(
    "/workspace/assets/{domain_code}/{asset_code}",
    response_model=AssetDetailResponse,
    response_model_by_alias=False,
)
async def asset_workspace_detail(
    domain_code: str,
    asset_code: str,
    gateway: SkyCommandGatewayDependency,
    settings: SettingsDependency,
) -> AssetDetailResponse:
    try:
        return await build_asset_detail(
            gateway,
            domain_code=domain_code,
            asset_code=asset_code,
            preview_enabled=settings.skycommand_offline_preview_enabled,
        )
    except SkyCommandClientError as error:
        status_code = 404 if error.status_code == 404 else 502
        raise HTTPException(status_code=status_code, detail=str(error)) from error

