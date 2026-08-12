import pytest
from fastapi.testclient import TestClient
from skydata_studio.api.routes import quality as quality_route
from skydata_studio.main import app
from skydata_studio.schemas.quality import (
    DbtQualityCheckSummary,
    DbtQualitySummary,
    QualityContractDefinition,
    QualityContractRuleDefinition,
    QualityContractSummary,
)
from skydata_studio.services.quality_contracts import evaluate_quality_contract

client = TestClient(app)


def _contract() -> QualityContractDefinition:
    return QualityContractDefinition(
        code="FED_FUNDS_RATE_DAILY_QUALITY",
        version="1.0.0",
        name="Federal Funds Rate Daily Quality Contract",
        description="Proof contract.",
        target_name="fct_fed_funds_rate_daily",
        layer="MART",
        enforcement_mode="BLOCK",
        minimum_pass_rate=1.0,
        rules=[
            QualityContractRuleDefinition(
                code="RATE_REQUIRED",
                label="Rate is present",
                quality_dimension="COMPLETENESS",
                test_kind="GENERIC",
                column_name="rate",
            ),
            QualityContractRuleDefinition(
                code="RATE_REASONABLE",
                label="Rate remains reasonable",
                quality_dimension="BUSINESS_RULE",
                test_kind="SINGULAR",
            ),
        ],
    )


def _check(
    *,
    name: str,
    dimension: str,
    test_kind: str,
    column_name: str | None,
    status: str = "PASS",
) -> DbtQualityCheckSummary:
    return DbtQualityCheckSummary.model_validate(
        {
            "unique_id": f"test.skydata_studio.{name}",
            "name": name,
            "test_kind": test_kind,
            "quality_dimension": dimension,
            "target_name": "fct_fed_funds_rate_daily",
            "target_resource_type": "MODEL",
            "layer": "MART",
            "column_name": column_name,
            "severity": "ERROR",
            "status": status,
            "failures": 0 if status == "PASS" else 1,
            "execution_time_ms": 75.0,
            "message": None,
            "path": "models/marts/schema.yml",
        }
    )


def _evidence(checks: list[DbtQualityCheckSummary]) -> DbtQualitySummary:
    return DbtQualitySummary(
        artifact_status="READY",
        trust_posture="TRUSTED",
        test_count=len(checks),
        passed_count=sum(check.status == "PASS" for check in checks),
        warning_count=sum(check.status == "WARN" for check in checks),
        failed_count=sum(check.status == "FAIL" for check in checks),
        error_count=sum(check.status == "ERROR" for check in checks),
        skipped_count=sum(check.status == "SKIP" for check in checks),
        unknown_count=sum(check.status == "UNKNOWN" for check in checks),
        source_test_count=0,
        model_test_count=len(checks),
        checks=checks,
    )


def test_quality_contract_is_compliant_when_required_evidence_passes() -> None:
    evidence = _evidence(
        [
            _check(
                name="not_null_daily_rate",
                dimension="COMPLETENESS",
                test_kind="GENERIC",
                column_name="rate",
            ),
            _check(
                name="assert_rate_reasonable",
                dimension="BUSINESS_RULE",
                test_kind="SINGULAR",
                column_name=None,
            ),
        ]
    )

    summary = evaluate_quality_contract(_contract(), evidence, source_path="proof.json")

    assert summary.contract_status == "COMPLIANT"
    assert summary.satisfied_rule_count == 2
    assert summary.blocking_rule_count == 0
    assert summary.pass_rate == 1.0
    assert all(rule.outcome == "PASS" for rule in summary.rules)


def test_quality_contract_blocks_when_required_rule_is_missing() -> None:
    evidence = _evidence(
        [
            _check(
                name="not_null_daily_rate",
                dimension="COMPLETENESS",
                test_kind="GENERIC",
                column_name="rate",
            )
        ]
    )

    summary = evaluate_quality_contract(_contract(), evidence, source_path="proof.json")

    assert summary.contract_status == "BLOCKED"
    assert summary.missing_rule_count == 1
    assert summary.blocking_rule_count == 1
    assert summary.pass_rate == 0.5


def test_quality_contract_is_pending_without_latest_run_evidence() -> None:
    evidence = DbtQualitySummary(
        artifact_status="PENDING",
        trust_posture="PENDING",
        test_count=2,
        passed_count=0,
        warning_count=0,
        failed_count=0,
        error_count=0,
        skipped_count=0,
        unknown_count=2,
        source_test_count=0,
        model_test_count=2,
        checks=[],
    )

    summary = evaluate_quality_contract(_contract(), evidence, source_path="proof.json")

    assert summary.contract_status == "PENDING"
    assert all(rule.outcome == "PENDING" for rule in summary.rules)


def test_quality_contract_endpoint_projects_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = QualityContractSummary(
        contract_code="FED_FUNDS_RATE_DAILY_QUALITY",
        contract_version="1.0.0",
        contract_name="Federal Funds Rate Daily Quality Contract",
        description="Proof contract.",
        target_name="fct_fed_funds_rate_daily",
        layer="MART",
        enforcement_mode="BLOCK",
        artifact_status="READY",
        evidence_trust_posture="TRUSTED",
        contract_status="COMPLIANT",
        minimum_pass_rate=1.0,
        pass_rate=1.0,
        required_rule_count=5,
        satisfied_rule_count=5,
        warning_rule_count=0,
        blocking_rule_count=0,
        missing_rule_count=0,
        source_path="contracts/quality/fed_funds_rate_daily.v1.json",
        rules=[],
    )
    monkeypatch.setattr(quality_route, "quality_contract_summary", lambda: expected)

    response = client.get("/api/v1/quality/contracts/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["phase"].startswith("Phase 7.2")
    assert payload["contract_status"] == "COMPLIANT"
    assert payload["required_rule_count"] == 5
