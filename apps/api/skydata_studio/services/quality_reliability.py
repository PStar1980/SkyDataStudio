from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from skydata_studio.models.quality import QualitySloObservation
from skydata_studio.schemas.quality import (
    QualityContractSummary,
    QualityIncidentSummary,
    QualityReliabilityObservationRead,
    QualityReliabilityStatus,
    QualityReliabilitySummary,
)
from skydata_studio.services.quality_contracts import quality_contract_summary


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_generated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _observation_key(contract: QualityContractSummary) -> str:
    evidence_key = (
        contract.evidence_invocation_id
        or contract.evidence_generated_at
        or f"{contract.artifact_status}:{contract.contract_status}"
    )
    return f"{contract.contract_code}:{contract.contract_version}:{evidence_key}"


def capture_quality_reliability_observation(
    session: Session,
    *,
    contract: QualityContractSummary,
    incidents: QualityIncidentSummary,
) -> bool:
    key = _observation_key(contract)
    existing = session.scalar(
        select(QualitySloObservation).where(QualitySloObservation.observation_key == key)
    )
    if existing is not None:
        return False

    session.add(
        QualitySloObservation(
            observation_key=key,
            contract_code=contract.contract_code,
            contract_version=contract.contract_version,
            evidence_invocation_id=contract.evidence_invocation_id,
            evidence_generated_at=_parse_generated_at(contract.evidence_generated_at),
            contract_status=contract.contract_status,
            artifact_status=contract.artifact_status,
            evidence_trust_posture=contract.evidence_trust_posture,
            pass_rate=contract.pass_rate,
            active_incident_count=incidents.active_count,
            blocking_active_incident_count=incidents.blocking_active_count,
            warning_active_incident_count=incidents.warning_active_count,
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return False
    return True


def quality_reliability_summary(
    session: Session,
    *,
    contract: QualityContractSummary | None = None,
    now: datetime | None = None,
) -> QualityReliabilitySummary:
    current = contract or quality_contract_summary()
    window_end = now or _utc_now()
    if window_end.tzinfo is None:
        window_end = window_end.replace(tzinfo=UTC)
    window_start = window_end - timedelta(days=current.slo_window_days)

    statement = (
        select(QualitySloObservation)
        .where(QualitySloObservation.contract_code == current.contract_code)
        .where(QualitySloObservation.captured_at >= window_start)
        .order_by(QualitySloObservation.captured_at.asc())
    )
    rows = list(session.scalars(statement).all())
    observations = [QualityReliabilityObservationRead.model_validate(row) for row in rows]

    total = len(observations)
    compliant = sum(item.contract_status == "COMPLIANT" for item in observations)
    degraded = sum(item.contract_status == "DEGRADED" for item in observations)
    blocked = sum(item.contract_status == "BLOCKED" for item in observations)
    pending = sum(item.contract_status == "PENDING" for item in observations)
    observed_rate = compliant / total if total else 0.0

    streak = 0
    for item in reversed(observations):
        if item.contract_status != "COMPLIANT":
            break
        streak += 1

    status: QualityReliabilityStatus
    if not observations:
        status = "PENDING"
    elif observed_rate < current.slo_minimum_compliance_rate:
        status = "BREACHED"
    elif current.contract_status != "COMPLIANT":
        status = "AT_RISK"
    else:
        status = "MEETING"

    return QualityReliabilitySummary(
        contract_code=current.contract_code,
        contract_version=current.contract_version,
        current_contract_status=current.contract_status,
        reliability_status=status,
        window_days=current.slo_window_days,
        minimum_compliance_rate=current.slo_minimum_compliance_rate,
        observed_compliance_rate=observed_rate,
        observation_count=total,
        compliant_count=compliant,
        degraded_count=degraded,
        blocked_count=blocked,
        pending_count=pending,
        current_compliant_streak=streak,
        window_start=window_start,
        window_end=window_end,
        observations=observations,
    )
