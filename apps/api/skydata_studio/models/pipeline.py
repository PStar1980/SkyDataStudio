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


class PipelineDefinition(TimestampMixin, Base):
    __tablename__ = "pipeline_definition"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", index=True)
    environment: Mapped[str] = mapped_column(String(40), default="development", index=True)
    execution_mode: Mapped[str] = mapped_column(String(40), default="LOCAL")
    mapping_id: Mapped[str | None] = mapped_column(
        ForeignKey("metadata_mapping.id"),
        index=True,
    )
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    versions: Mapped[list[PipelineVersion]] = relationship(
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="PipelineVersion.version_number",
    )


class PipelineVersion(TimestampMixin, Base):
    __tablename__ = "pipeline_version"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "version_number", name="uq_pipeline_version_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    pipeline_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_definition.id", ondelete="CASCADE"),
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT")
    notes: Mapped[str | None] = mapped_column(Text)
    execution_contract: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    pipeline: Mapped[PipelineDefinition] = relationship(back_populates="versions")
    parameters: Mapped[list[PipelineParameter]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="PipelineParameter.ordinal_position",
    )
    steps: Mapped[list[PipelineStep]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="PipelineStep.execution_order",
    )


class PipelineParameter(TimestampMixin, Base):
    __tablename__ = "pipeline_parameter"
    __table_args__ = (
        UniqueConstraint("version_id", "code", name="uq_pipeline_parameter_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_version.id", ondelete="CASCADE"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(160))
    data_type: Mapped[str] = mapped_column(String(40), default="STRING")
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_value: Mapped[Any | None] = mapped_column(JSON)
    ordinal_position: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str | None] = mapped_column(Text)

    version: Mapped[PipelineVersion] = relationship(back_populates="parameters")


class PipelineStep(TimestampMixin, Base):
    __tablename__ = "pipeline_step"
    __table_args__ = (
        UniqueConstraint("version_id", "code", name="uq_pipeline_step_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_version.id", ondelete="CASCADE"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(200))
    step_type: Mapped[str] = mapped_column(String(40), default="SQL")
    execution_order: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="READY")
    mapping_id: Mapped[str | None] = mapped_column(ForeignKey("metadata_mapping.id"), index=True)
    source_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("metadata_asset.id"),
        index=True,
    )
    target_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("metadata_asset.id"),
        index=True,
    )
    sql_text: Mapped[str | None] = mapped_column(Text)
    script_path: Mapped[str | None] = mapped_column(String(500))
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    continue_on_failure: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    version: Mapped[PipelineVersion] = relationship(back_populates="steps")
    dependencies: Mapped[list[PipelineStepDependency]] = relationship(
        foreign_keys="PipelineStepDependency.step_id",
        back_populates="step",
        cascade="all, delete-orphan",
    )
    dependents: Mapped[list[PipelineStepDependency]] = relationship(
        foreign_keys="PipelineStepDependency.depends_on_step_id",
        back_populates="depends_on_step",
        cascade="all, delete-orphan",
    )


class PipelineStepDependency(TimestampMixin, Base):
    __tablename__ = "pipeline_step_dependency"
    __table_args__ = (
        UniqueConstraint(
            "step_id",
            "depends_on_step_id",
            name="uq_pipeline_step_dependency",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    step_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_step.id", ondelete="CASCADE"),
        index=True,
    )
    depends_on_step_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_step.id", ondelete="CASCADE"),
        index=True,
    )
    dependency_condition: Mapped[str] = mapped_column(String(40), default="SUCCESS")

    step: Mapped[PipelineStep] = relationship(
        foreign_keys=[step_id],
        back_populates="dependencies",
    )
    depends_on_step: Mapped[PipelineStep] = relationship(
        foreign_keys=[depends_on_step_id],
        back_populates="dependents",
    )
