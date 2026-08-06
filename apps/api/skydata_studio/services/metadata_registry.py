from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from skydata_studio.integrations.skycommand.dependencies import SkyCommandGateway
from skydata_studio.models.metadata import (
    MetadataAsset,
    MetadataConnection,
    MetadataDependency,
    MetadataDomain,
    MetadataField,
    MetadataNamespace,
    MetadataSystem,
)
from skydata_studio.schemas.metadata import (
    MetadataAssetCreate,
    MetadataAssetDetail,
    MetadataAssetList,
    MetadataAssetListItem,
    MetadataDependencyRead,
    MetadataDomainRead,
    MetadataFieldRead,
    MetadataNamespaceRead,
    MetadataSummary,
    MetadataSyncResult,
    MetadataSystemRead,
)
from skydata_studio.services.asset_workspace import build_asset_workspace


class MetadataRegistryConflictError(ValueError):
    """Raised when a registry write violates an intentional business key."""


class MetadataRegistryNotFoundError(LookupError):
    """Raised when a requested registry entity does not exist."""


def _metadata_asset_options() -> tuple[Any, ...]:
    return (
        selectinload(MetadataAsset.domain),
        selectinload(MetadataAsset.system),
        selectinload(MetadataAsset.namespace),
        selectinload(MetadataAsset.fields),
        selectinload(MetadataAsset.upstream_dependencies).selectinload(
            MetadataDependency.upstream_asset
        ),
        selectinload(MetadataAsset.downstream_dependencies).selectinload(
            MetadataDependency.downstream_asset
        ),
    )


def _asset_item(asset: MetadataAsset) -> MetadataAssetListItem:
    return MetadataAssetListItem(
        id=asset.id,
        code=asset.code,
        name=asset.name,
        description=asset.description,
        asset_type=asset.asset_type,
        layer=asset.layer,
        physical_name=asset.physical_name,
        domain_code=asset.domain.code,
        domain_name=asset.domain.name,
        system_code=asset.system.code,
        system_name=asset.system.name,
        namespace_code=asset.namespace.code,
        namespace_name=asset.namespace.name,
        owner_name=asset.owner_name,
        classification=asset.classification,
        criticality=asset.criticality,
        status=asset.status,
        source_system_code=asset.source_system_code,
        source_asset_code=asset.source_asset_code,
        source_contract_version=asset.source_contract_version,
        tags=list(asset.tags),
        field_count=len(asset.fields),
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _dependency_read(dependency: MetadataDependency) -> MetadataDependencyRead:
    return MetadataDependencyRead(
        id=dependency.id,
        dependency_type=dependency.dependency_type,
        upstream_asset_id=dependency.upstream_asset_id,
        upstream_asset_code=dependency.upstream_asset.code,
        upstream_asset_name=dependency.upstream_asset.name,
        downstream_asset_id=dependency.downstream_asset_id,
        downstream_asset_code=dependency.downstream_asset.code,
        downstream_asset_name=dependency.downstream_asset.name,
        description=dependency.description,
    )


def _asset_detail(asset: MetadataAsset) -> MetadataAssetDetail:
    return MetadataAssetDetail(
        **_asset_item(asset).model_dump(),
        fields=[
            MetadataFieldRead(
                id=field.id,
                code=field.code,
                name=field.name,
                data_type=field.data_type,
                ordinal_position=field.ordinal_position,
                nullable=field.nullable,
                key_field=field.key_field,
                classification=field.classification,
                description=field.description,
            )
            for field in asset.fields
        ],
        upstream_dependencies=[
            _dependency_read(dependency) for dependency in asset.upstream_dependencies
        ],
        downstream_dependencies=[
            _dependency_read(dependency) for dependency in asset.downstream_dependencies
        ],
        attributes=dict(asset.attributes),
    )


def _ensure_domain(
    session: Session,
    *,
    code: str,
    name: str,
    description: str | None = None,
) -> MetadataDomain:
    domain = session.scalar(select(MetadataDomain).where(MetadataDomain.code == code))
    if domain is None:
        domain = MetadataDomain(code=code, name=name, description=description)
        session.add(domain)
        session.flush()
    else:
        domain.name = name
        if description:
            domain.description = description
    return domain


def _ensure_system(
    session: Session,
    *,
    code: str,
    name: str,
    system_type: str,
    description: str | None = None,
) -> MetadataSystem:
    system = session.scalar(select(MetadataSystem).where(MetadataSystem.code == code))
    if system is None:
        system = MetadataSystem(
            code=code,
            name=name,
            system_type=system_type,
            description=description,
        )
        session.add(system)
        session.flush()
    else:
        system.name = name
        system.system_type = system_type
        if description:
            system.description = description
    return system


def _ensure_connection(
    session: Session,
    *,
    system: MetadataSystem,
    code: str,
    name: str,
    endpoint_label: str,
) -> MetadataConnection:
    connection = session.scalar(
        select(MetadataConnection).where(
            MetadataConnection.system_id == system.id,
            MetadataConnection.code == code,
        )
    )
    if connection is None:
        connection = MetadataConnection(
            system=system,
            code=code,
            name=name,
            connection_type="API",
            endpoint_label=endpoint_label,
            secret_reference="SKYCOMMAND_API_TOKEN",
            read_only=True,
        )
        session.add(connection)
        session.flush()
    else:
        connection.endpoint_label = endpoint_label
    return connection


def _ensure_namespace(
    session: Session,
    *,
    system: MetadataSystem,
    connection: MetadataConnection | None,
    code: str,
    name: str,
    namespace_type: str,
    physical_name: str | None,
    description: str | None = None,
) -> MetadataNamespace:
    namespace = session.scalar(
        select(MetadataNamespace).where(
            MetadataNamespace.system_id == system.id,
            MetadataNamespace.code == code,
        )
    )
    if namespace is None:
        namespace = MetadataNamespace(
            system=system,
            connection=connection,
            code=code,
            name=name,
            namespace_type=namespace_type,
            physical_name=physical_name,
            description=description,
        )
        session.add(namespace)
        session.flush()
    else:
        namespace.name = name
        namespace.namespace_type = namespace_type
        namespace.physical_name = physical_name
        if connection is not None:
            namespace.connection = connection
    return namespace


def metadata_summary(session: Session) -> MetadataSummary:
    layers = Counter(
        session.scalars(select(MetadataAsset.layer)).all()
    )
    return MetadataSummary(
        status="CONNECTED",
        message="SkyData Studio metadata registry is available.",
        domains=session.scalar(select(func.count()).select_from(MetadataDomain)) or 0,
        systems=session.scalar(select(func.count()).select_from(MetadataSystem)) or 0,
        connections=session.scalar(select(func.count()).select_from(MetadataConnection)) or 0,
        namespaces=session.scalar(select(func.count()).select_from(MetadataNamespace)) or 0,
        assets=session.scalar(select(func.count()).select_from(MetadataAsset)) or 0,
        fields=session.scalar(select(func.count()).select_from(MetadataField)) or 0,
        dependencies=session.scalar(select(func.count()).select_from(MetadataDependency)) or 0,
        layers=dict(sorted(layers.items())),
    )


def list_domains(session: Session) -> list[MetadataDomainRead]:
    domains = session.scalars(select(MetadataDomain).order_by(MetadataDomain.name)).all()
    return [
        MetadataDomainRead(
            id=domain.id,
            code=domain.code,
            name=domain.name,
            description=domain.description,
            active=domain.active,
        )
        for domain in domains
    ]


def list_systems(session: Session) -> list[MetadataSystemRead]:
    systems = session.scalars(select(MetadataSystem).order_by(MetadataSystem.name)).all()
    return [
        MetadataSystemRead(
            id=system.id,
            code=system.code,
            name=system.name,
            system_type=system.system_type,
            description=system.description,
            active=system.active,
        )
        for system in systems
    ]


def list_namespaces(session: Session) -> list[MetadataNamespaceRead]:
    namespaces = session.scalars(
        select(MetadataNamespace)
        .options(selectinload(MetadataNamespace.system))
        .order_by(MetadataNamespace.name)
    ).all()
    return [
        MetadataNamespaceRead(
            id=namespace.id,
            code=namespace.code,
            name=namespace.name,
            namespace_type=namespace.namespace_type,
            physical_name=namespace.physical_name,
            environment=namespace.environment,
            system_code=namespace.system.code,
            system_name=namespace.system.name,
        )
        for namespace in namespaces
    ]


def list_metadata_assets(
    session: Session,
    *,
    domain_code: str | None = None,
    system_code: str | None = None,
    layer: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> MetadataAssetList:
    filters: list[Any] = []
    if domain_code:
        filters.append(MetadataDomain.code == domain_code.upper())
    if system_code:
        filters.append(MetadataSystem.code == system_code.upper())
    if layer:
        filters.append(MetadataAsset.layer == layer.upper())
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                MetadataAsset.code.ilike(pattern),
                MetadataAsset.name.ilike(pattern),
                MetadataAsset.description.ilike(pattern),
                MetadataAsset.physical_name.ilike(pattern),
            )
        )

    count_statement = (
        select(func.count())
        .select_from(MetadataAsset)
        .join(MetadataAsset.domain)
        .join(MetadataAsset.system)
        .where(*filters)
    )
    statement = (
        select(MetadataAsset)
        .join(MetadataAsset.domain)
        .join(MetadataAsset.system)
        .options(*_metadata_asset_options())
        .where(*filters)
        .order_by(MetadataAsset.layer, MetadataAsset.name)
        .limit(limit)
        .offset(offset)
    )
    assets = session.scalars(statement).unique().all()
    total = session.scalar(count_statement) or 0
    return MetadataAssetList(total=total, items=[_asset_item(asset) for asset in assets])


def get_metadata_asset(session: Session, asset_id: str) -> MetadataAssetDetail:
    asset = session.scalar(
        select(MetadataAsset)
        .options(*_metadata_asset_options())
        .where(MetadataAsset.id == asset_id)
    )
    if asset is None:
        raise MetadataRegistryNotFoundError("Metadata asset was not found.")
    return _asset_detail(asset)


def register_metadata_asset(
    session: Session,
    payload: MetadataAssetCreate,
) -> MetadataAssetDetail:
    domain = _ensure_domain(
        session,
        code=payload.domain.code,
        name=payload.domain.name or payload.domain.code.replace("_", " ").title(),
        description=payload.domain.description,
    )
    system = _ensure_system(
        session,
        code=payload.system.code,
        name=payload.system.name or payload.system.code.replace("_", " ").title(),
        system_type=payload.system_type,
        description=payload.system.description,
    )
    namespace = _ensure_namespace(
        session,
        system=system,
        connection=None,
        code=payload.namespace.code,
        name=payload.namespace.name or payload.namespace.code.replace("_", " ").title(),
        namespace_type=payload.namespace_type,
        physical_name=payload.physical_namespace,
        description=payload.namespace.description,
    )
    existing = session.scalar(
        select(MetadataAsset).where(
            MetadataAsset.namespace_id == namespace.id,
            MetadataAsset.code == payload.code,
        )
    )
    if existing is not None:
        raise MetadataRegistryConflictError(
            f"Asset {namespace.code}.{payload.code} is already registered."
        )

    asset = MetadataAsset(
        domain=domain,
        system=system,
        namespace=namespace,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        asset_type=payload.asset_type,
        layer=payload.layer,
        physical_name=payload.physical_name,
        owner_name=payload.owner_name,
        owner_email=payload.owner_email,
        classification=payload.classification,
        criticality=payload.criticality,
        tags=payload.tags,
        attributes={"registration_mode": "MANUAL"},
    )
    asset.fields = [
        MetadataField(
            code=field.code,
            name=field.name or field.code.replace("_", " ").title(),
            data_type=field.data_type,
            ordinal_position=field.ordinal_position,
            nullable=field.nullable,
            key_field=field.key_field,
            classification=field.classification,
            description=field.description,
        )
        for field in payload.fields
    ]
    session.add(asset)
    session.commit()
    return get_metadata_asset(session, asset.id)


def _storage_parts(storage_relation: str | None) -> tuple[str, str | None]:
    if not storage_relation:
        return "UNMAPPED", None
    if "." not in storage_relation:
        return "DEFAULT", storage_relation
    schema_name, relation_name = storage_relation.split(".", maxsplit=1)
    return schema_name.upper(), relation_name


async def synchronize_skycommand_assets(
    session: Session,
    gateway: SkyCommandGateway,
) -> MetadataSyncResult:
    workspace = await build_asset_workspace(
        gateway,
        limit=500,
        offset=0,
        preview_enabled=False,
    )
    system = _ensure_system(
        session,
        code="SKYCOMMAND",
        name="SkyCommand",
        system_type="APPLICATION",
        description="Trusted ingestion and catalogue boundary for SkyData Studio.",
    )
    connection = _ensure_connection(
        session,
        system=system,
        code="SKYCOMMAND_API",
        name="SkyCommand read-only API",
        endpoint_label=gateway.base_url,
    )

    created = 0
    updated = 0
    domain_ids: set[str] = set()
    namespace_ids: set[str] = set()
    for item in workspace.items:
        domain = _ensure_domain(
            session,
            code=item.domain_code,
            name=item.domain_name,
            description=f"Imported from SkyCommand domain {item.domain_code}.",
        )
        schema_code, relation_name = _storage_parts(item.storage_relation)
        namespace = _ensure_namespace(
            session,
            system=system,
            connection=connection,
            code=schema_code,
            name=schema_code.replace("_", " ").title(),
            namespace_type="SCHEMA",
            physical_name=schema_code.lower() if schema_code != "UNMAPPED" else None,
        )
        domain_ids.add(domain.id)
        namespace_ids.add(namespace.id)
        asset = session.scalar(
            select(MetadataAsset).where(
                MetadataAsset.namespace_id == namespace.id,
                MetadataAsset.code == item.asset_code,
            )
        )
        tag_values = {"skycommand", item.domain_code.lower()}
        if item.source_code:
            tag_values.add(item.source_code.lower())
        if item.frequency_code:
            tag_values.add(item.frequency_code.lower())
        tags = sorted(tag_values)
        attributes = {
            "freshness_status": item.freshness_status,
            "freshness_reason": item.freshness_reason,
            "source_latest_date": (
                item.source_latest_date.isoformat() if item.source_latest_date else None
            ),
            "target_latest_date": (
                item.target_latest_date.isoformat() if item.target_latest_date else None
            ),
            "target_row_count": item.target_row_count,
            "last_run_status": item.last_run_status,
            "quality_issue_count": item.quality_issue_count,
            "provider_name": item.provider_name,
        }
        if asset is None:
            asset = MetadataAsset(
                domain=domain,
                system=system,
                namespace=namespace,
                code=item.asset_code,
                name=item.asset_name,
                description=item.asset_description,
                asset_type=("TIME_SERIES" if item.asset_kind_code == "TIME_SERIES" else "TABLE"),
                layer="RAW",
                physical_name=relation_name,
                classification="INTERNAL",
                criticality=item.criticality_code,
                source_system_code=item.source_code,
                source_asset_code=item.asset_code,
                source_contract_version=item.contract_version,
                tags=tags,
                attributes=attributes,
            )
            session.add(asset)
            created += 1
        else:
            asset.domain = domain
            asset.name = item.asset_name
            asset.description = item.asset_description
            asset.physical_name = relation_name
            asset.criticality = item.criticality_code
            asset.source_system_code = item.source_code
            asset.source_asset_code = item.asset_code
            asset.source_contract_version = item.contract_version
            asset.tags = tags
            asset.attributes = attributes
            updated += 1

    session.commit()
    return MetadataSyncResult(
        mode="LIVE",
        imported=len(workspace.items),
        created=created,
        updated=updated,
        domains=len(domain_ids),
        namespaces=len(namespace_ids),
        message="SkyCommand trusted assets synchronized into the Studio metadata registry.",
    )
