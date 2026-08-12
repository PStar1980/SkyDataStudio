from collections.abc import Generator

import pytest
from skydata_studio.models.quality import QualityIncident, QualityIncidentEvent
from skydata_studio.schemas.quality import (
    QualityContractRuleEvaluation,
    QualityContractSummary,
    QualityIncidentAction,
)
from skydata_studio.services.quality_incidents import (
    QualityIncidentTransitionError,
    acknowledge_quality_incident,
    quality_incident_summary,
    reconcile_quality_incidents,
    resolve_quality_incident,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    QualityIncident.__table__.create(engine)
    QualityIncidentEvent.__table__.create(engine)
    with Session(engine) as db_session:
        yield db_session


def _contract(outcome: str) -> QualityContractSummary:
    matched_status = "PASS" if outcome == "PASS" else "FAIL"
    return QualityContractSummary.model_validate(
        {
            "contract_code": "FED_FUNDS_RATE_DAILY_QUALITY",
            "contract_version": "1.0.0",
            "contract_name": "Federal Funds Rate Daily Quality Contract",
            "description": "Proof contract.",
            "target_name": "fct_fed_funds_rate_daily",
            "layer": "MART",
            "enforcement_mode": "BLOCK",
            "artifact_status": "READY",
            "evidence_trust_posture": "TRUSTED" if outcome == "PASS" else "BLOCKED",
            "contract_status": "COMPLIANT" if outcome == "PASS" else "BLOCKED",
            "minimum_pass_rate": 1.0,
            "pass_rate": 1.0 if outcome == "PASS" else 0.0,
            "required_rule_count": 1,
            "satisfied_rule_count": 1 if outcome == "PASS" else 0,
            "warning_rule_count": 1 if outcome == "WARN" else 0,
            "blocking_rule_count": 0 if outcome in {"PASS", "WARN"} else 1,
            "missing_rule_count": 1 if outcome == "MISSING" else 0,
            "source_path": "contracts/quality/fed_funds_rate_daily.v1.json",
            "rules": [
                QualityContractRuleEvaluation.model_validate(
                    {
                        "code": "RATE_REQUIRED",
                        "label": "Rate is present",
                        "quality_dimension": "COMPLETENESS",
                        "test_kind": "GENERIC",
                        "column_name": "rate",
                        "required_status": "PASS",
                        "outcome": outcome,
                        "matched_check_name": "not_null_fct_fed_funds_rate_daily_rate",
                        "matched_status": matched_status,
                        "matched_severity": "ERROR",
                        "message": "Synthetic lifecycle proof.",
                    }
                )
            ],
        }
    )


def test_reconcile_opens_durable_incident_for_blocking_rule(session: Session) -> None:
    result = reconcile_quality_incidents(session, contract=_contract("BLOCK"))

    assert result.created_count == 1
    assert result.summary.active_count == 1
    incident = result.summary.incidents[0]
    assert incident.status == "OPEN"
    assert incident.severity == "BLOCKING"
    assert incident.occurrence_count == 1
    assert [event.event_type for event in incident.events] == ["OPENED"]


def test_incident_can_be_acknowledged_and_manually_resolved(session: Session) -> None:
    opened = reconcile_quality_incidents(session, contract=_contract("BLOCK"))
    incident_id = opened.summary.incidents[0].id

    acknowledged = acknowledge_quality_incident(
        session,
        incident_id,
        QualityIncidentAction(actor="paul", note="Investigating upstream evidence."),
    )
    resolved = resolve_quality_incident(
        session,
        incident_id,
        QualityIncidentAction(actor="paul", note="Remediation verified."),
    )

    assert acknowledged.status == "ACKNOWLEDGED"
    assert acknowledged.acknowledged_by == "paul"
    assert resolved.status == "RESOLVED"
    assert resolved.resolution_note == "Remediation verified."
    assert [event.event_type for event in resolved.events] == [
        "OPENED",
        "ACKNOWLEDGED",
        "RESOLVED",
    ]


def test_reconcile_auto_resolves_incident_when_contract_returns_to_pass(session: Session) -> None:
    reconcile_quality_incidents(session, contract=_contract("BLOCK"))

    result = reconcile_quality_incidents(session, contract=_contract("PASS"))

    assert result.resolved_count == 1
    assert result.summary.active_count == 0
    incident = result.summary.incidents[0]
    assert incident.status == "RESOLVED"
    assert incident.resolution_note == "Latest quality contract evidence returned to PASS."
    assert incident.events[-1].event_type == "RESOLVED"
    assert incident.events[-1].actor == "SYSTEM"


def test_failed_evidence_reopens_resolved_incident_as_new_occurrence(session: Session) -> None:
    opened = reconcile_quality_incidents(session, contract=_contract("BLOCK"))
    incident_id = opened.summary.incidents[0].id
    resolve_quality_incident(
        session,
        incident_id,
        QualityIncidentAction(actor="operator", note="Temporary remediation."),
    )

    result = reconcile_quality_incidents(session, contract=_contract("BLOCK"))
    summary = quality_incident_summary(session, contract=_contract("BLOCK"))

    assert result.reopened_count == 1
    assert summary.active_count == 1
    incident = summary.incidents[0]
    assert incident.status == "OPEN"
    assert incident.occurrence_count == 2
    assert incident.events[-1].event_type == "REOPENED"

    acknowledge_quality_incident(
        session,
        incident_id,
        QualityIncidentAction(actor="operator", note="Owned again."),
    )
    with pytest.raises(QualityIncidentTransitionError):
        acknowledge_quality_incident(
            session,
            incident_id,
            QualityIncidentAction(actor="operator", note="Duplicate acknowledgement."),
        )
