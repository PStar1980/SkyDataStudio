from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from skydata_studio.models.quality import QualityIncident, QualityIncidentEvent
from skydata_studio.schemas.quality import (
    QualityContractRuleEvaluation,
    QualityContractSummary,
    QualityIncidentAction,
    QualityIncidentRead,
    QualityIncidentReconcileResult,
    QualityIncidentSummary,
)
from skydata_studio.services.quality_contracts import quality_contract_summary

IssueOutcome = Literal["WARN", "BLOCK", "MISSING"]


class QualityIncidentNotFoundError(ValueError):
    pass


class QualityIncidentTransitionError(ValueError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _incident_key(contract_code: str, rule_code: str) -> str:
    return f"{contract_code}:{rule_code}"


def _issue_outcome(rule: QualityContractRuleEvaluation) -> IssueOutcome | None:
    if rule.outcome in {"WARN", "BLOCK", "MISSING"}:
        return cast(IssueOutcome, rule.outcome)
    return None


def _severity(outcome: IssueOutcome) -> Literal["WARNING", "BLOCKING"]:
    return "WARNING" if outcome == "WARN" else "BLOCKING"


def _event(
    incident: QualityIncident,
    event_type: Literal["OPENED", "REOPENED", "ACKNOWLEDGED", "RESOLVED"],
    *,
    actor: str | None,
    note: str | None,
    evidence_outcome: Literal["PASS", "WARN", "BLOCK", "MISSING"] | None,
) -> None:
    incident.events.append(
        QualityIncidentEvent(
            event_type=event_type,
            actor=actor,
            note=note,
            evidence_outcome=evidence_outcome,
        )
    )


def _active_incidents(session: Session, contract_code: str) -> list[QualityIncident]:
    statement = (
        select(QualityIncident)
        .where(QualityIncident.contract_code == contract_code)
        .options(selectinload(QualityIncident.events))
    )
    return list(session.scalars(statement).unique().all())


def _read(incident: QualityIncident) -> QualityIncidentRead:
    return QualityIncidentRead.model_validate(incident)


def _summary_from_contract(
    session: Session,
    contract: QualityContractSummary,
) -> QualityIncidentSummary:
    incidents = _active_incidents(session, contract.contract_code)
    incidents.sort(
        key=lambda incident: (
            incident.status == "RESOLVED",
            -incident.updated_at.timestamp(),
        )
    )
    active = [incident for incident in incidents if incident.status != "RESOLVED"]
    return QualityIncidentSummary(
        contract_code=contract.contract_code,
        contract_status=contract.contract_status,
        artifact_status=contract.artifact_status,
        total_count=len(incidents),
        active_count=len(active),
        open_count=sum(incident.status == "OPEN" for incident in incidents),
        acknowledged_count=sum(incident.status == "ACKNOWLEDGED" for incident in incidents),
        resolved_count=sum(incident.status == "RESOLVED" for incident in incidents),
        blocking_active_count=sum(
            incident.status != "RESOLVED" and incident.severity == "BLOCKING"
            for incident in incidents
        ),
        warning_active_count=sum(
            incident.status != "RESOLVED" and incident.severity == "WARNING"
            for incident in incidents
        ),
        incidents=[_read(incident) for incident in incidents],
    )


def quality_incident_summary(
    session: Session,
    *,
    contract: QualityContractSummary | None = None,
) -> QualityIncidentSummary:
    return _summary_from_contract(session, contract or quality_contract_summary())


def reconcile_quality_incidents(
    session: Session,
    *,
    contract: QualityContractSummary | None = None,
) -> QualityIncidentReconcileResult:
    current = contract or quality_contract_summary()
    incidents = _active_incidents(session, current.contract_code)
    by_key = {incident.incident_key: incident for incident in incidents}
    now = _utc_now()
    created_count = 0
    reopened_count = 0
    resolved_count = 0
    active_rule_keys: set[str] = set()

    for rule in current.rules:
        key = _incident_key(current.contract_code, rule.code)
        active_rule_keys.add(key)
        incident = by_key.get(key)
        issue = _issue_outcome(rule)

        if issue is not None:
            if incident is None:
                incident = QualityIncident(
                    incident_key=key,
                    contract_code=current.contract_code,
                    contract_version=current.contract_version,
                    rule_code=rule.code,
                    rule_label=rule.label,
                    target_name=current.target_name,
                    layer=current.layer,
                    quality_dimension=rule.quality_dimension,
                    severity=_severity(issue),
                    status="OPEN",
                    evidence_outcome=issue,
                    matched_check_name=rule.matched_check_name,
                    matched_status=rule.matched_status,
                    message=rule.message,
                    occurrence_count=1,
                    first_detected_at=now,
                    last_detected_at=now,
                )
                _event(
                    incident,
                    "OPENED",
                    actor="SYSTEM",
                    note="Latest contract evidence created a durable quality incident.",
                    evidence_outcome=issue,
                )
                session.add(incident)
                by_key[key] = incident
                created_count += 1
                continue

            incident.contract_version = current.contract_version
            incident.rule_label = rule.label
            incident.target_name = current.target_name
            incident.layer = current.layer
            incident.quality_dimension = rule.quality_dimension
            incident.severity = _severity(issue)
            incident.evidence_outcome = issue
            incident.matched_check_name = rule.matched_check_name
            incident.matched_status = rule.matched_status
            incident.message = rule.message
            incident.last_detected_at = now

            if incident.status == "RESOLVED":
                incident.status = "OPEN"
                incident.occurrence_count += 1
                incident.acknowledged_at = None
                incident.acknowledged_by = None
                incident.resolved_at = None
                incident.resolution_note = None
                _event(
                    incident,
                    "REOPENED",
                    actor="SYSTEM",
                    note="Failing contract evidence returned after resolution.",
                    evidence_outcome=issue,
                )
                reopened_count += 1
            continue

        if rule.outcome == "PASS" and incident is not None and incident.status != "RESOLVED":
            incident.status = "RESOLVED"
            incident.resolved_at = now
            incident.resolution_note = "Latest quality contract evidence returned to PASS."
            _event(
                incident,
                "RESOLVED",
                actor="SYSTEM",
                note=incident.resolution_note,
                evidence_outcome="PASS",
            )
            resolved_count += 1

    for incident in incidents:
        if incident.incident_key in active_rule_keys or incident.status == "RESOLVED":
            continue
        incident.status = "RESOLVED"
        incident.resolved_at = now
        incident.resolution_note = "Rule is no longer present in the active quality contract."
        _event(
            incident,
            "RESOLVED",
            actor="SYSTEM",
            note=incident.resolution_note,
            evidence_outcome=None,
        )
        resolved_count += 1

    session.commit()
    return QualityIncidentReconcileResult(
        created_count=created_count,
        reopened_count=reopened_count,
        resolved_count=resolved_count,
        summary=_summary_from_contract(session, current),
    )


def _get_incident(session: Session, incident_id: str) -> QualityIncident:
    statement = (
        select(QualityIncident)
        .where(QualityIncident.id == incident_id)
        .options(selectinload(QualityIncident.events))
    )
    incident = session.scalar(statement)
    if incident is None:
        raise QualityIncidentNotFoundError(f"Quality incident {incident_id} was not found.")
    return incident


def acknowledge_quality_incident(
    session: Session,
    incident_id: str,
    action: QualityIncidentAction,
) -> QualityIncidentRead:
    incident = _get_incident(session, incident_id)
    if incident.status == "RESOLVED":
        raise QualityIncidentTransitionError("Resolved incidents cannot be acknowledged.")
    if incident.status == "ACKNOWLEDGED":
        raise QualityIncidentTransitionError("Quality incident is already acknowledged.")

    now = _utc_now()
    incident.status = "ACKNOWLEDGED"
    incident.acknowledged_at = now
    incident.acknowledged_by = action.actor
    _event(
        incident,
        "ACKNOWLEDGED",
        actor=action.actor,
        note=action.note,
        evidence_outcome=cast(IssueOutcome, incident.evidence_outcome),
    )
    session.commit()
    session.refresh(incident)
    return _read(_get_incident(session, incident.id))


def resolve_quality_incident(
    session: Session,
    incident_id: str,
    action: QualityIncidentAction,
) -> QualityIncidentRead:
    incident = _get_incident(session, incident_id)
    if incident.status == "RESOLVED":
        raise QualityIncidentTransitionError("Quality incident is already resolved.")

    now = _utc_now()
    incident.status = "RESOLVED"
    incident.resolved_at = now
    incident.resolution_note = action.note or "Resolved manually from SkyData Studio."
    _event(
        incident,
        "RESOLVED",
        actor=action.actor,
        note=incident.resolution_note,
        evidence_outcome=None,
    )
    session.commit()
    session.refresh(incident)
    return _read(_get_incident(session, incident.id))
