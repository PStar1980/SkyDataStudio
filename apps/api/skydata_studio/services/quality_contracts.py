from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

from skydata_studio.schemas.quality import (
    DbtQualityCheckSummary,
    DbtQualitySummary,
    QualityContractDefinition,
    QualityContractRuleDefinition,
    QualityContractRuleEvaluation,
    QualityContractSummary,
)
from skydata_studio.services.dbt_quality import dbt_quality_summary


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_contract_path() -> Path:
    return _repository_root() / "contracts" / "quality" / "fed_funds_rate_daily.v1.json"


def _read_contract(path: Path) -> QualityContractDefinition:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected an object in quality contract {path}.")
    return QualityContractDefinition.model_validate(cast(dict[str, Any], payload))


def _matches_rule(
    check: DbtQualityCheckSummary,
    *,
    contract: QualityContractDefinition,
    rule: QualityContractRuleDefinition,
) -> bool:
    return (
        check.target_name == contract.target_name
        and check.layer == contract.layer
        and check.quality_dimension == rule.quality_dimension
        and check.test_kind == rule.test_kind
        and check.column_name == rule.column_name
    )


def _rule_evaluation(
    *,
    contract: QualityContractDefinition,
    rule: QualityContractRuleDefinition,
    evidence: DbtQualitySummary,
) -> QualityContractRuleEvaluation:
    if evidence.artifact_status != "READY":
        return QualityContractRuleEvaluation(
            **rule.model_dump(),
            outcome="PENDING",
            message="Latest dbt run-result evidence is not ready yet.",
        )

    matches = [
        check
        for check in evidence.checks
        if _matches_rule(check, contract=contract, rule=rule)
    ]
    if not matches:
        return QualityContractRuleEvaluation(
            **rule.model_dump(),
            outcome="MISSING",
            message="No latest dbt quality check satisfies this contract selector.",
        )

    check = matches[0]
    if check.status == "PASS":
        outcome: Literal["PASS", "WARN", "BLOCK"] = "PASS"
        message = "Required dbt quality evidence is present and passing."
    elif check.status == "WARN":
        outcome = "WARN"
        message = "Required evidence is present but the latest dbt result is warning."
    else:
        outcome = "BLOCK"
        message = f"Required evidence is present but the latest dbt result is {check.status}."

    if len(matches) > 1:
        outcome = "BLOCK"
        message = "More than one dbt check matched this contract selector; tighten the rule."

    return QualityContractRuleEvaluation(
        **rule.model_dump(),
        outcome=outcome,
        matched_check_name=check.name,
        matched_status=check.status,
        matched_severity=check.severity,
        message=message,
    )


def evaluate_quality_contract(
    contract: QualityContractDefinition,
    evidence: DbtQualitySummary,
    *,
    source_path: str,
) -> QualityContractSummary:
    rules = [
        _rule_evaluation(contract=contract, rule=rule, evidence=evidence)
        for rule in contract.rules
    ]
    required = len(rules)
    satisfied = sum(rule.outcome == "PASS" for rule in rules)
    warnings = sum(rule.outcome == "WARN" for rule in rules)
    missing = sum(rule.outcome == "MISSING" for rule in rules)
    blocking = sum(rule.outcome in {"BLOCK", "MISSING"} for rule in rules)
    pass_rate = satisfied / required if required else 1.0

    if evidence.artifact_status != "READY":
        contract_status: Literal["COMPLIANT", "DEGRADED", "BLOCKED", "PENDING"] = "PENDING"
    elif blocking or pass_rate < contract.minimum_pass_rate:
        contract_status = "BLOCKED" if contract.enforcement_mode == "BLOCK" else "DEGRADED"
    elif warnings:
        contract_status = "DEGRADED"
    else:
        contract_status = "COMPLIANT"

    return QualityContractSummary(
        contract_code=contract.code,
        contract_version=contract.version,
        contract_name=contract.name,
        description=contract.description,
        target_name=contract.target_name,
        layer=contract.layer,
        enforcement_mode=contract.enforcement_mode,
        artifact_status=evidence.artifact_status,
        evidence_trust_posture=evidence.trust_posture,
        contract_status=contract_status,
        minimum_pass_rate=contract.minimum_pass_rate,
        pass_rate=pass_rate,
        required_rule_count=required,
        satisfied_rule_count=satisfied,
        warning_rule_count=warnings,
        blocking_rule_count=blocking,
        missing_rule_count=missing,
        source_path=source_path,
        rules=rules,
    )


def quality_contract_summary(
    *,
    contract_path: Path | None = None,
    target_dir: Path | None = None,
) -> QualityContractSummary:
    path = contract_path or _default_contract_path()
    contract = _read_contract(path)
    evidence = dbt_quality_summary(target_dir)
    try:
        source_path = path.relative_to(_repository_root()).as_posix()
    except ValueError:
        source_path = path.as_posix()
    return evaluate_quality_contract(contract, evidence, source_path=source_path)
