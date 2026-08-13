from __future__ import annotations

from collections import defaultdict
from typing import Literal

from sqlalchemy.orm import Session

from skydata_studio.schemas.lineage import (
    FieldLineageNode,
    FieldLineageSummary,
    LineageNode,
    LineageSummary,
    LineageTrustOverlay,
    LineageTrustSummary,
)
from skydata_studio.schemas.quality import (
    DbtQualityCheckSummary,
    DbtQualitySummary,
    QualityContractRuleEvaluation,
    QualityContractSummary,
    QualityIncidentRead,
    QualityIncidentSummary,
)
from skydata_studio.services.dbt_quality import dbt_quality_summary
from skydata_studio.services.lineage import field_lineage_summary, lineage_summary
from skydata_studio.services.quality_contracts import quality_contract_summary
from skydata_studio.services.quality_incidents import quality_incident_summary

TrustStatus = Literal["TRUSTED", "DEGRADED", "BLOCKED", "PENDING"]


def _overlay_status(
    checks: list[DbtQualityCheckSummary],
    rules: list[QualityContractRuleEvaluation],
    incidents: list[QualityIncidentRead],
    *,
    evidence_ready: bool,
) -> TrustStatus:
    if any(
        incident.severity == "BLOCKING" and incident.status != "RESOLVED"
        for incident in incidents
    ):
        return "BLOCKED"
    if any(rule.outcome in {"BLOCK", "MISSING"} for rule in rules):
        return "BLOCKED"
    if any(check.status in {"FAIL", "ERROR"} for check in checks):
        return "BLOCKED"
    if any(
        incident.severity == "WARNING" and incident.status != "RESOLVED"
        for incident in incidents
    ):
        return "DEGRADED"
    if any(rule.outcome == "WARN" for rule in rules):
        return "DEGRADED"
    if any(check.status == "WARN" for check in checks):
        return "DEGRADED"
    if not evidence_ready or any(rule.outcome == "PENDING" for rule in rules):
        return "PENDING"
    return "TRUSTED"


def _quality_dimensions(
    checks: list[DbtQualityCheckSummary],
    rules: list[QualityContractRuleEvaluation],
    incidents: list[QualityIncidentRead],
) -> list[str]:
    dimensions: set[str] = set()
    dimensions.update(check.quality_dimension for check in checks)
    dimensions.update(rule.quality_dimension for rule in rules)
    dimensions.update(incident.quality_dimension for incident in incidents)
    return sorted(dimensions)


def _overlay(
    *,
    node_id: str,
    node_label: str,
    scope: Literal["ASSET", "FIELD"],
    layer: str,
    relation: str | None,
    checks: list[DbtQualityCheckSummary],
    rules: list[QualityContractRuleEvaluation],
    incidents: list[QualityIncidentRead],
    evidence_ready: bool,
) -> LineageTrustOverlay:
    active_incidents = [incident for incident in incidents if incident.status != "RESOLVED"]
    return LineageTrustOverlay(
        node_id=node_id,
        node_label=node_label,
        scope=scope,
        layer=layer,
        relation=relation,
        quality_status=_overlay_status(
            checks,
            rules,
            incidents,
            evidence_ready=evidence_ready,
        ),
        check_count=len(checks),
        passed_check_count=sum(check.status == "PASS" for check in checks),
        warning_check_count=sum(check.status == "WARN" for check in checks),
        failed_check_count=sum(check.status in {"FAIL", "ERROR"} for check in checks),
        contract_rule_count=len(rules),
        satisfied_contract_rule_count=sum(rule.outcome == "PASS" for rule in rules),
        active_incident_count=len(active_incidents),
        blocking_incident_count=sum(
            incident.severity == "BLOCKING" for incident in active_incidents
        ),
        quality_dimensions=_quality_dimensions(checks, rules, incidents),
    )


def compose_lineage_trust_summary(
    *,
    asset_lineage: LineageSummary,
    field_lineage: FieldLineageSummary,
    quality: DbtQualitySummary,
    contract: QualityContractSummary,
    incidents: QualityIncidentSummary,
) -> LineageTrustSummary:
    asset_by_target: dict[str, LineageNode] = {
        node.label.lower(): node
        for node in asset_lineage.nodes
        if node.node_type in {"DBT_SOURCE", "DBT_MODEL"}
    }
    field_by_target: dict[tuple[str, str], FieldLineageNode] = {}
    for node in field_lineage.nodes:
        if (
            node.parent_label is None
            or node.node_type not in {"DBT_SOURCE_FIELD", "DBT_MODEL_FIELD"}
        ):
            continue
        field_by_target[(node.parent_label.lower(), node.field_name.lower())] = node

    checks_by_target: dict[str, list[DbtQualityCheckSummary]] = defaultdict(list)
    checks_by_field: dict[tuple[str, str], list[DbtQualityCheckSummary]] = defaultdict(list)
    for check in quality.checks:
        target = check.target_name.lower()
        checks_by_target[target].append(check)
        if check.column_name:
            checks_by_field[(target, check.column_name.lower())].append(check)

    rules_by_target: dict[str, list[QualityContractRuleEvaluation]] = defaultdict(list)
    rules_by_field: dict[tuple[str, str], list[QualityContractRuleEvaluation]] = defaultdict(list)
    rule_by_code = {rule.code: rule for rule in contract.rules}
    contract_target = contract.target_name.lower()
    for rule in contract.rules:
        rules_by_target[contract_target].append(rule)
        if rule.column_name:
            rules_by_field[(contract_target, rule.column_name.lower())].append(rule)

    incidents_by_target: dict[str, list[QualityIncidentRead]] = defaultdict(list)
    incidents_by_field: dict[tuple[str, str], list[QualityIncidentRead]] = defaultdict(list)
    for incident in incidents.incidents:
        target = incident.target_name.lower()
        incidents_by_target[target].append(incident)
        incident_rule = rule_by_code.get(incident.rule_code)
        if incident_rule and incident_rule.column_name:
            incidents_by_field[(target, incident_rule.column_name.lower())].append(incident)

    evidence_ready = quality.artifact_status == "READY" and contract.artifact_status == "READY"
    overlays: list[LineageTrustOverlay] = []

    protected_targets = set(checks_by_target) | set(rules_by_target) | set(incidents_by_target)
    for target in sorted(protected_targets):
        asset_node = asset_by_target.get(target)
        if asset_node is None:
            continue
        overlays.append(
            _overlay(
                node_id=asset_node.id,
                node_label=asset_node.label,
                scope="ASSET",
                layer=asset_node.layer,
                relation=asset_node.relation,
                checks=checks_by_target[target],
                rules=rules_by_target[target],
                incidents=incidents_by_target[target],
                evidence_ready=evidence_ready,
            )
        )

    protected_fields = set(checks_by_field) | set(rules_by_field) | set(incidents_by_field)
    for target_field in sorted(protected_fields):
        field_node = field_by_target.get(target_field)
        if field_node is None:
            continue
        overlays.append(
            _overlay(
                node_id=field_node.id,
                node_label=field_node.label,
                scope="FIELD",
                layer=field_node.layer,
                relation=field_node.relation,
                checks=checks_by_field[target_field],
                rules=rules_by_field[target_field],
                incidents=incidents_by_field[target_field],
                evidence_ready=evidence_ready,
            )
        )

    if asset_lineage.artifact_status == "MISSING" and field_lineage.artifact_status == "MISSING":
        artifact_status: Literal["READY", "PARTIAL", "MISSING"] = "MISSING"
    elif (
        asset_lineage.artifact_status == "READY"
        and field_lineage.artifact_status == "READY"
        and evidence_ready
        and overlays
    ):
        artifact_status = "READY"
    else:
        artifact_status = "PARTIAL"

    return LineageTrustSummary(
        artifact_status=artifact_status,
        evidence_trust_posture=quality.trust_posture,
        contract_status=contract.contract_status,
        check_count=quality.test_count,
        passed_check_count=quality.passed_count,
        required_contract_rule_count=contract.required_rule_count,
        satisfied_contract_rule_count=contract.satisfied_rule_count,
        active_incident_count=incidents.active_count,
        blocking_incident_count=incidents.blocking_active_count,
        protected_asset_count=sum(overlay.scope == "ASSET" for overlay in overlays),
        protected_field_count=sum(overlay.scope == "FIELD" for overlay in overlays),
        overlays=overlays,
    )


def lineage_trust_summary(session: Session) -> LineageTrustSummary:
    contract = quality_contract_summary()
    return compose_lineage_trust_summary(
        asset_lineage=lineage_summary(session),
        field_lineage=field_lineage_summary(session),
        quality=dbt_quality_summary(),
        contract=contract,
        incidents=quality_incident_summary(session, contract=contract),
    )
