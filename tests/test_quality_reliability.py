from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from skydata_studio.models.quality import QualitySloObservation
from skydata_studio.schemas.quality import QualityContractSummary, QualityIncidentSummary
from skydata_studio.services.quality_reliability import (
    capture_quality_reliability_observation,
    quality_reliability_summary,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    QualitySloObservation.__table__.create(engine)
    with Session(engine) as db_session:
        yield db_session


def _contract(
    status: str = "COMPLIANT",
    *,
    invocation_id: str = "invocation-1",
    pass_rate: float = 1.0,
) -> QualityContractSummary:
    return QualityContractSummary.model_validate(
        {
            "contract_code": "FED_FUNDS_RATE_DAILY_QUALITY",
            "contract_version": "1.1.0",
            "contract_name": "Federal Funds Rate Daily Quality Contract",
            "description": "Reliability proof contract.",
            "target_name": "fct_fed_funds_rate_daily",
            "layer": "MART",
            "enforcement_mode": "BLOCK",
            "artifact_status": "READY",
            "evidence_trust_posture": "TRUSTED" if status == "COMPLIANT" else "BLOCKED",
            "contract_status": status,
            "minimum_pass_rate": 1.0,
            "pass_rate": pass_rate,
            "required_rule_count": 5,
            "satisfied_rule_count": 5 if status == "COMPLIANT" else 4,
            "warning_rule_count": 0,
            "blocking_rule_count": 0 if status == "COMPLIANT" else 1,
            "missing_rule_count": 0,
            "source_path": "contracts/quality/fed_funds_rate_daily.v1.json",
            "evidence_invocation_id": invocation_id,
            "evidence_generated_at": "2026-08-12T18:36:30.823071Z",
            "slo_window_days": 30,
            "slo_minimum_compliance_rate": 0.99,
            "rules": [],
        }
    )


def _incidents(active: int = 0, blocking: int = 0) -> QualityIncidentSummary:
    return QualityIncidentSummary.model_validate(
        {
            "contract_code": "FED_FUNDS_RATE_DAILY_QUALITY",
            "contract_status": "COMPLIANT" if active == 0 else "BLOCKED",
            "artifact_status": "READY",
            "total_count": active,
            "active_count": active,
            "open_count": active,
            "acknowledged_count": 0,
            "resolved_count": 0,
            "blocking_active_count": blocking,
            "warning_active_count": max(active - blocking, 0),
            "incidents": [],
        }
    )


def test_reliability_capture_is_idempotent_per_dbt_invocation(session: Session) -> None:
    contract = _contract()

    first = capture_quality_reliability_observation(
        session, contract=contract, incidents=_incidents()
    )
    second = capture_quality_reliability_observation(
        session, contract=contract, incidents=_incidents()
    )

    assert first is True
    assert second is False
    assert len(session.query(QualitySloObservation).all()) == 1


def test_reliability_meets_slo_for_clean_observation(session: Session) -> None:
    contract = _contract()
    capture_quality_reliability_observation(session, contract=contract, incidents=_incidents())

    summary = quality_reliability_summary(
        session,
        contract=contract,
        now=datetime.now(UTC) + timedelta(seconds=1),
    )

    assert summary.reliability_status == "MEETING"
    assert summary.observation_count == 1
    assert summary.compliant_count == 1
    assert summary.observed_compliance_rate == 1.0
    assert summary.current_compliant_streak == 1


def test_reliability_breaches_slo_when_blocking_observation_is_captured(
    session: Session,
) -> None:
    contract = _contract("BLOCKED", invocation_id="invocation-2", pass_rate=0.8)
    capture_quality_reliability_observation(
        session, contract=contract, incidents=_incidents(active=1, blocking=1)
    )

    summary = quality_reliability_summary(
        session,
        contract=contract,
        now=datetime.now(UTC) + timedelta(seconds=1),
    )

    assert summary.reliability_status == "BREACHED"
    assert summary.blocked_count == 1
    assert summary.observed_compliance_rate == 0.0
    assert summary.observations[0].blocking_active_incident_count == 1


def test_reliability_is_pending_until_first_observation_exists(session: Session) -> None:
    summary = quality_reliability_summary(session, contract=_contract())

    assert summary.reliability_status == "PENDING"
    assert summary.observation_count == 0
    assert summary.observed_compliance_rate == 0.0
