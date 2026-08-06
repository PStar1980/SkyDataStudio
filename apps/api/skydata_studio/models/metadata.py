from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from skydata_studio.db.base import Base


def _uuid() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )


class MetadataDomain(TimestampMixin, Base):
    __tablename__ = "metadata_domain"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assets: Mapped[list[MetadataAsset]] = relationship(back_populates="domain")


class MetadataSystem(TimestampMixin, Base):
    __tablename__ = "metadata_system"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    system_type: Mapped[str] = mapped_column(String(40), default="APPLICATION")
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    connections: Mapped[list[MetadataConnection]] = relationship(back_populates="system")
    namespaces: Mapped[list[MetadataNamespace]] = relationship(back_populates="system")
    assets: Mapped[list[MetadataAsset]] = relationship(back_populates="system")


class MetadataConnection(TimestampMixin, Base):
    __tablename__ = "metadata_connection"
    __table_args__ = (UniqueConstraint("system_id", "code", name="uq_metadata_connection"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    system_id: Mapped[str] = mapped_column(ForeignKey("metadata_system.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(160))
    connection_type: Mapped[str] = mapped_column(String(40), default="API")
    environment: Mapped[str] = mapped_column(String(40), default="development")
    endpoint_label: Mapped[str | None] = mapped_column(String(255))
    database_name: Mapped[str | None] = mapped_column(String(128))
    secret_reference: Mapped[str | None] = mapped_column(String(160))
    read_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    system: Mapped[MetadataSystem] = relationship(back_populates="connections")
    namespaces: Mapped[list[MetadataNamespace]] = relationship(back_populates="connection")


class MetadataNamespace(TimestampMixin, Base):
    __tablename__ = "metadata_namespace"
    __table_args__ = (UniqueConstraint("system_id", "code", name="uq_metadata_namespace"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    system_id: Mapped[str] = mapped_column(ForeignKey("metadata_system.id"), index=True)
    connection_id: Mapped[str | None] = mapped_column(
        ForeignKey("metadata_connection.id"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(96))
    name: Mapped[str] = mapped_column(String(160))
    namespace_type: Mapped[str] = mapped_column(String(40), default="SCHEMA")
    physical_name: Mapped[str | None] = mapped_column(String(255))
    environment: Mapped[str] = mapped_column(String(40), default="development")
    description: Mapped[str | None] = mapped_column(Text)

    system: Mapped[MetadataSystem] = relationship(back_populates="namespaces")
    connection: Mapped[MetadataConnection | None] = relationship(back_populates="namespaces")
    assets: Mapped[list[MetadataAsset]] = relationship(back_populates="namespace")


class MetadataAsset(TimestampMixin, Base):
    __tablename__ = "metadata_asset"
    __table_args__ = (
        UniqueConstraint("namespace_id", "code", name="uq_metadata_asset_namespace_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    domain_id: Mapped[str] = mapped_column(ForeignKey("metadata_domain.id"), index=True)
    system_id: Mapped[str] = mapped_column(ForeignKey("metadata_system.id"), index=True)
    namespace_id: Mapped[str] = mapped_column(ForeignKey("metadata_namespace.id"), index=True)
    code: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    asset_type: Mapped[str] = mapped_column(String(40), default="TABLE")
    layer: Mapped[str] = mapped_column(String(40), default="RAW", index=True)
    physical_name: Mapped[str | None] = mapped_column(String(255))
    owner_name: Mapped[str | None] = mapped_column(String(160))
    owner_email: Mapped[str | None] = mapped_column(String(255))
    classification: Mapped[str] = mapped_column(String(40), default="INTERNAL")
    criticality: Mapped[str] = mapped_column(String(40), default="STANDARD")
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    source_system_code: Mapped[str | None] = mapped_column(String(64))
    source_asset_code: Mapped[str | None] = mapped_column(String(128))
    source_contract_version: Mapped[str | None] = mapped_column(String(80))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    domain: Mapped[MetadataDomain] = relationship(back_populates="assets")
    system: Mapped[MetadataSystem] = relationship(back_populates="assets")
    namespace: Mapped[MetadataNamespace] = relationship(back_populates="assets")
    fields: Mapped[list[MetadataField]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="MetadataField.ordinal_position",
    )
    upstream_dependencies: Mapped[list[MetadataDependency]] = relationship(
        foreign_keys="MetadataDependency.downstream_asset_id",
        back_populates="downstream_asset",
        cascade="all, delete-orphan",
    )
    downstream_dependencies: Mapped[list[MetadataDependency]] = relationship(
        foreign_keys="MetadataDependency.upstream_asset_id",
        back_populates="upstream_asset",
        cascade="all, delete-orphan",
    )
    outbound_mappings: Mapped[list[MetadataMapping]] = relationship(
        foreign_keys="MetadataMapping.source_asset_id",
        back_populates="source_asset",
        cascade="all, delete-orphan",
    )
    inbound_mappings: Mapped[list[MetadataMapping]] = relationship(
        foreign_keys="MetadataMapping.target_asset_id",
        back_populates="target_asset",
        cascade="all, delete-orphan",
    )


class MetadataField(TimestampMixin, Base):
    __tablename__ = "metadata_field"
    __table_args__ = (UniqueConstraint("asset_id", "code", name="uq_metadata_field"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(ForeignKey("metadata_asset.id"), index=True)
    code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(160))
    data_type: Mapped[str] = mapped_column(String(80))
    ordinal_position: Mapped[int] = mapped_column(Integer, default=1)
    nullable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    key_field: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    classification: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)

    asset: Mapped[MetadataAsset] = relationship(back_populates="fields")


class MetadataDependency(TimestampMixin, Base):
    __tablename__ = "metadata_dependency"
    __table_args__ = (
        UniqueConstraint(
            "upstream_asset_id",
            "downstream_asset_id",
            "dependency_type",
            name="uq_metadata_dependency",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    upstream_asset_id: Mapped[str] = mapped_column(
        ForeignKey("metadata_asset.id"),
        index=True,
    )
    downstream_asset_id: Mapped[str] = mapped_column(
        ForeignKey("metadata_asset.id"),
        index=True,
    )
    dependency_type: Mapped[str] = mapped_column(String(40), default="TRANSFORMS")
    description: Mapped[str | None] = mapped_column(Text)

    upstream_asset: Mapped[MetadataAsset] = relationship(
        foreign_keys=[upstream_asset_id],
        back_populates="downstream_dependencies",
    )
    downstream_asset: Mapped[MetadataAsset] = relationship(
        foreign_keys=[downstream_asset_id],
        back_populates="upstream_dependencies",
    )


class MetadataMapping(TimestampMixin, Base):
    __tablename__ = "metadata_mapping"
    __table_args__ = (
        UniqueConstraint("code", name="uq_metadata_mapping_code"),
        UniqueConstraint(
            "source_asset_id",
            "target_asset_id",
            "mapping_type",
            name="uq_metadata_mapping_edge",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(255))
    source_asset_id: Mapped[str] = mapped_column(
        ForeignKey("metadata_asset.id"),
        index=True,
    )
    target_asset_id: Mapped[str] = mapped_column(
        ForeignKey("metadata_asset.id"),
        index=True,
    )
    mapping_type: Mapped[str] = mapped_column(String(40), default="TRANSFORM")
    load_strategy: Mapped[str] = mapped_column(String(40), default="FULL_REPLACE")
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", index=True)
    grain: Mapped[str | None] = mapped_column(String(255))
    business_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    transformation_expression: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    source_asset: Mapped[MetadataAsset] = relationship(
        foreign_keys=[source_asset_id],
        back_populates="outbound_mappings",
    )
    target_asset: Mapped[MetadataAsset] = relationship(
        foreign_keys=[target_asset_id],
        back_populates="inbound_mappings",
    )
    field_mappings: Mapped[list[MetadataFieldMapping]] = relationship(
        back_populates="mapping",
        cascade="all, delete-orphan",
        order_by="MetadataFieldMapping.ordinal_position",
    )


class MetadataFieldMapping(TimestampMixin, Base):
    __tablename__ = "metadata_field_mapping"
    __table_args__ = (
        UniqueConstraint(
            "mapping_id",
            "target_field_code",
            name="uq_metadata_field_mapping_target",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mapping_id: Mapped[str] = mapped_column(
        ForeignKey("metadata_mapping.id", ondelete="CASCADE"),
        index=True,
    )
    source_field_code: Mapped[str | None] = mapped_column(String(128))
    target_field_code: Mapped[str] = mapped_column(String(128))
    target_data_type: Mapped[str] = mapped_column(String(80))
    transformation_type: Mapped[str] = mapped_column(String(40), default="DIRECT")
    expression: Mapped[str | None] = mapped_column(Text)
    ordinal_position: Mapped[int] = mapped_column(Integer, default=1)
    nullable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    key_field: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    mapping: Mapped[MetadataMapping] = relationship(back_populates="field_mappings")
