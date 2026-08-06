from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from skydata_studio.db.session import SessionDependency
from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.dependencies import SkyCommandGatewayDependency
from skydata_studio.schemas.metadata import (
    MetadataAssetCreate,
    MetadataAssetDetail,
    MetadataAssetFieldsReplace,
    MetadataAssetGovernanceUpdate,
    MetadataAssetList,
    MetadataDomainRead,
    MetadataMappingCreate,
    MetadataMappingDetail,
    MetadataMappingList,
    MetadataMappingSummary,
    MetadataNamespaceRead,
    MetadataSummary,
    MetadataSyncResult,
    MetadataSystemRead,
)
from skydata_studio.services.metadata_registry import (
    MetadataRegistryConflictError,
    MetadataRegistryNotFoundError,
    create_metadata_mapping,
    get_metadata_asset,
    get_metadata_mapping,
    list_domains,
    list_metadata_assets,
    list_metadata_mappings,
    list_namespaces,
    list_systems,
    mapping_summary,
    metadata_summary,
    register_metadata_asset,
    replace_metadata_asset_fields,
    synchronize_skycommand_assets,
    update_metadata_asset_governance,
)

router = APIRouter()


def _database_unavailable(error: SQLAlchemyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "SkyData Studio metadata storage is unavailable. Start studio-postgres and run "
            "uv run python scripts/bootstrap_metadata.py."
        ),
    )


def _not_found(error: MetadataRegistryNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def _conflict(error: MetadataRegistryConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("/summary", response_model=MetadataSummary)
def registry_summary(session: SessionDependency) -> MetadataSummary:
    try:
        return metadata_summary(session)
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/domains", response_model=list[MetadataDomainRead])
def registry_domains(session: SessionDependency) -> list[MetadataDomainRead]:
    try:
        return list_domains(session)
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/systems", response_model=list[MetadataSystemRead])
def registry_systems(session: SessionDependency) -> list[MetadataSystemRead]:
    try:
        return list_systems(session)
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/namespaces", response_model=list[MetadataNamespaceRead])
def registry_namespaces(session: SessionDependency) -> list[MetadataNamespaceRead]:
    try:
        return list_namespaces(session)
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/assets", response_model=MetadataAssetList)
def registry_assets(
    session: SessionDependency,
    domain_code: Annotated[str | None, Query(alias="domainCode")] = None,
    system_code: Annotated[str | None, Query(alias="systemCode")] = None,
    layer: str | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MetadataAssetList:
    try:
        return list_metadata_assets(
            session,
            domain_code=domain_code,
            system_code=system_code,
            layer=layer,
            search=search,
            limit=limit,
            offset=offset,
        )
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/assets/{asset_id}", response_model=MetadataAssetDetail)
def registry_asset(asset_id: str, session: SessionDependency) -> MetadataAssetDetail:
    try:
        return get_metadata_asset(session, asset_id)
    except MetadataRegistryNotFoundError as error:
        raise _not_found(error) from error
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.post(
    "/assets",
    response_model=MetadataAssetDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_registry_asset(
    payload: MetadataAssetCreate,
    session: SessionDependency,
) -> MetadataAssetDetail:
    try:
        return register_metadata_asset(session, payload)
    except MetadataRegistryConflictError as error:
        raise _conflict(error) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _database_unavailable(error) from error


@router.patch("/assets/{asset_id}/governance", response_model=MetadataAssetDetail)
def update_registry_asset_governance(
    asset_id: str,
    payload: MetadataAssetGovernanceUpdate,
    session: SessionDependency,
) -> MetadataAssetDetail:
    try:
        return update_metadata_asset_governance(session, asset_id, payload)
    except MetadataRegistryNotFoundError as error:
        raise _not_found(error) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _database_unavailable(error) from error


@router.put("/assets/{asset_id}/fields", response_model=MetadataAssetDetail)
def replace_registry_asset_fields(
    asset_id: str,
    payload: MetadataAssetFieldsReplace,
    session: SessionDependency,
) -> MetadataAssetDetail:
    try:
        return replace_metadata_asset_fields(session, asset_id, payload)
    except MetadataRegistryNotFoundError as error:
        raise _not_found(error) from error
    except MetadataRegistryConflictError as error:
        raise _conflict(error) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _database_unavailable(error) from error


@router.get("/mappings/summary", response_model=MetadataMappingSummary)
def registry_mapping_summary(session: SessionDependency) -> MetadataMappingSummary:
    try:
        return mapping_summary(session)
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/mappings", response_model=MetadataMappingList)
def registry_mappings(
    session: SessionDependency,
    source_asset_id: Annotated[str | None, Query(alias="sourceAssetId")] = None,
    target_asset_id: Annotated[str | None, Query(alias="targetAssetId")] = None,
    mapping_status: Annotated[str | None, Query(alias="status")] = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MetadataMappingList:
    try:
        return list_metadata_mappings(
            session,
            source_asset_id=source_asset_id,
            target_asset_id=target_asset_id,
            status=mapping_status,
            search=search,
            limit=limit,
            offset=offset,
        )
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/mappings/{mapping_id}", response_model=MetadataMappingDetail)
def registry_mapping(
    mapping_id: str,
    session: SessionDependency,
) -> MetadataMappingDetail:
    try:
        return get_metadata_mapping(session, mapping_id)
    except MetadataRegistryNotFoundError as error:
        raise _not_found(error) from error
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.post(
    "/mappings",
    response_model=MetadataMappingDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_registry_mapping(
    payload: MetadataMappingCreate,
    session: SessionDependency,
) -> MetadataMappingDetail:
    try:
        return create_metadata_mapping(session, payload)
    except MetadataRegistryNotFoundError as error:
        raise _not_found(error) from error
    except MetadataRegistryConflictError as error:
        raise _conflict(error) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _database_unavailable(error) from error


@router.post("/sync/skycommand", response_model=MetadataSyncResult)
async def sync_registry_from_skycommand(
    session: SessionDependency,
    gateway: SkyCommandGatewayDependency,
) -> MetadataSyncResult:
    try:
        return await synchronize_skycommand_assets(session, gateway)
    except SkyCommandClientError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _database_unavailable(error) from error
