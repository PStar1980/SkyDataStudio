from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from skydata_studio.db.base import Base


def _uuid() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(UTC)


class QualityIncident(Base):
    __tablename__ = "quality_incident"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_key: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    contract_code: Mapped[str] = mapped_column(String(160), index=True)
    contract_version: Mapped[str] = mapped_column(String(40))
    rule_code: Mapped[str] = mapped_column(String(160), index=True)
    rule_label: Mapped[str] = mapped_column(String(255))
    target_name: Mapped[str] = mapped_column(String(255), index=True)
    layer: Mapped[str] = mapped_column(String(40), index=True)
    quality_dimension: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="OPEN", index=True)
    evidence_outcome: Mapped[str] = mapped_column(String(40))
    matched_check_name: Mapped[str | None] = mapped_column(String(500))
    matched_status: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(String(160))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    events: Mapped[list[QualityIncidentEvent]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="QualityIncidentEvent.created_at",
    )


class QualityIncidentEvent(Base):
    __tablename__ = "quality_incident_event"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("quality_incident.id", ondelete="CASCADE"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    actor: Mapped[str | None] = mapped_column(String(160))
    note: Mapped[str | None] = mapped_column(Text)
    evidence_outcome: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    incident: Mapped[QualityIncident] = relationship(back_populates="events")
