from datetime import UTC, datetime

from skydata_studio.schemas.lineage import (
    FieldLineageImpactSummary,
    FieldLineageNode,
    FieldLineageSummary,
    LineageImpactSummary,
    LineageNode,
    LineageSummary,
)
from skydata_studio.schemas.quality import (
    DbtQualityCheckSummary,
    DbtQualitySummary,
    QualityContractRuleEvaluation,
    QualityContractSummary,
    QualityIncidentRead,
    QualityIncidentSummary,
)
from skydata_studio.services.lineage_trust import compose_lineage_trust_summary


def _asset_lineage() -> LineageSummary:
    nodes = [
        LineageNode(
            id="dbt:source.skydata_studio.studio_curated.fed_funds_rate",
            label="fed_funds_rate",
            node_type="DBT_SOURCE",
            layer="SOURCE",
            system="dbt",
            relation="mart.fed_funds_rate",
            status="READY",
        ),
        LineageNode(
            id="dbt:model.skydata_studio.stg_fed_funds_rate",
            label="stg_fed_funds_rate",
            node_type="DBT_MODEL",
            layer="STAGING",
            system="dbt",
            relation="dbt_staging.stg_fed_funds_rate",
            status="READY",
        ),
        LineageNode(
            id="dbt:model.skydata_studio.int_fed_funds_rate_changes",
            label="int_fed_funds_rate_changes",
            node_type="DBT_MODEL",
            layer="INTERMEDIATE",
            system="dbt",
            relation="dbt_intermediate.int_fed_funds_rate_changes",
            status="READY",
        ),
        LineageNode(
            id="dbt:model.skydata_studio.fct_fed_funds_rate_daily",
            label="fct_fed_funds_rate_daily",
            node_type="DBT_MODEL",
            layer="MART",
            system="dbt",
            relation="dbt_mart.fct_fed_funds_rate_daily",
            status="READY",
        ),
    ]
    return LineageSummary(
        artifact_status="READY",
        metadata_mapping_count=1,
        dbt_model_count=3,
        semantic_model_count=1,
        metric_count=4,
        node_count=len(nodes),
        edge_count=0,
        nodes=nodes,
        edges=[],
        default_impact=LineageImpactSummary(
            downstream_node_count=0,
            affected_model_count=0,
            affected_semantic_model_count=0,
            affected_metric_count=0,
            affected_layers=[],
            nodes=[],
        ),
    )


def _field_lineage() -> FieldLineageSummary:
    fields = [
        ("fed_funds_rate", "SOURCE", "DBT_SOURCE_FIELD", "observation_date"),
        ("fed_funds_rate", "SOURCE", "DBT_SOURCE_FIELD", "rate"),
        ("stg_fed_funds_rate", "STAGING", "DBT_MODEL_FIELD", "observation_date"),
        ("stg_fed_funds_rate", "STAGING", "DBT_MODEL_FIELD", "rate"),
        (
            "int_fed_funds_rate_changes",
            "INTERMEDIATE",
            "DBT_MODEL_FIELD",
            "observation_date",
        ),
        ("int_fed_funds_rate_changes", "INTERMEDIATE", "DBT_MODEL_FIELD", "rate"),
        ("fct_fed_funds_rate_daily", "MART", "DBT_MODEL_FIELD", "observation_date"),
        ("fct_fed_funds_rate_daily", "MART", "DBT_MODEL_FIELD", "rate"),
        ("fct_fed_funds_rate_daily", "MART", "DBT_MODEL_FIELD", "rate_direction"),
    ]
    nodes = [
        FieldLineageNode(
            id=f"field:{parent}:{field_name}",
            label=f"{parent}.{field_name}",
            field_name=field_name,
            node_type=node_type,
            layer=layer,
            system="dbt",
            relation=parent,
            parent_node_id=f"parent:{parent}",
            parent_label=parent,
            status="READY",
        )
        for parent, layer, node_type, field_name in fields
    ]
    return FieldLineageSummary(
        artifact_status="READY",
        field_mapping_count=2,
        dbt_annotated_column_count=18,
        metric_binding_count=4,
        node_count=len(nodes),
        edge_count=0,
        nodes=nodes,
        edges=[],
        default_impact=FieldLineageImpactSummary(
            downstream_node_count=0,
            affected_field_count=0,
            affected_metric_count=0,
            affected_relations=[],
            affected_layers=[],
            nodes=[],
        ),
    )


def _check(
    name: str,
    target: str,
    layer: str,
    dimension: str,
    column: str | None,
    *,
    status: str = "PASS",
    test_kind: str = "GENERIC",
) -> DbtQualityCheckSummary:
    return DbtQualityCheckSummary.model_validate(
        {
            "unique_id": f"test.{name}",
            "name": name,
            "test_kind": test_kind,
            "quality_dimension": dimension,
            "target_name": target,
            "target_resource_type": "SOURCE" if layer == "SOURCE" else "MODEL",
            "layer": layer,
            "column_name": column,
            "severity": "ERROR",
            "status": status,
            "failures": 0 if status == "PASS" else 1,
            "path": "models/schema.yml",
        }
    )


def _quality(*, status: str = "PASS") -> DbtQualitySummary:
    checks = [
        _check(
            "source_date_present",
            "fed_funds_rate",
            "SOURCE",
            "COMPLETENESS",
            "observation_date",
            status=status,
        ),
        _check(
            "source_rate_present",
            "fed_funds_rate",
            "SOURCE",
            "COMPLETENESS",
            "rate",
            status=status,
        ),
        _check(
            "source_date_unique",
            "fed_funds_rate",
            "SOURCE",
            "UNIQUENESS",
            "observation_date",
            status=status,
        ),
        _check(
            "stg_date_present",
            "stg_fed_funds_rate",
            "STAGING",
            "COMPLETENESS",
            "observation_date",
            status=status,
        ),
        _check(
            "stg_rate_present",
            "stg_fed_funds_rate",
            "STAGING",
            "COMPLETENESS",
            "rate",
            status=status,
        ),
        _check(
            "stg_date_unique",
            "stg_fed_funds_rate",
            "STAGING",
            "UNIQUENESS",
            "observation_date",
            status=status,
        ),
        _check(
            "int_date_present",
            "int_fed_funds_rate_changes",
            "INTERMEDIATE",
            "COMPLETENESS",
            "observation_date",
            status=status,
        ),
        _check(
            "int_rate_present",
            "int_fed_funds_rate_changes",
            "INTERMEDIATE",
            "COMPLETENESS",
            "rate",
            status=status,
        ),
        _check(
            "int_date_unique",
            "int_fed_funds_rate_changes",
            "INTERMEDIATE",
            "UNIQUENESS",
            "observation_date",
            status=status,
        ),
        _check(
            "mart_date_present",
            "fct_fed_funds_rate_daily",
            "MART",
            "COMPLETENESS",
            "observation_date",
            status=status,
        ),
        _check(
            "mart_rate_present",
            "fct_fed_funds_rate_daily",
            "MART",
            "COMPLETENESS",
            "rate",
            status=status,
        ),
        _check(
            "mart_date_unique",
            "fct_fed_funds_rate_daily",
            "MART",
            "UNIQUENESS",
            "observation_date",
            status=status,
        ),
        _check(
            "mart_direction_valid",
            "fct_fed_funds_rate_daily",
            "MART",
            "VALIDITY",
            "rate_direction",
            status=status,
        ),
        _check(
            "mart_rate_reasonable",
            "fct_fed_funds_rate_daily",
            "MART",
            "BUSINESS_RULE",
            None,
            status=status,
            test_kind="SINGULAR",
        ),
    ]
    failed = 0 if status == "PASS" else len(checks)
    return DbtQualitySummary(
        artifact_status="READY",
        trust_posture="TRUSTED" if status == "PASS" else "BLOCKED",
        test_count=len(checks),
        passed_count=len(checks) - failed,
        warning_count=0,
        failed_count=failed,
        error_count=0,
        skipped_count=0,
        unknown_count=0,
        source_test_count=3,
        model_test_count=11,
        checks=checks,
    )


def _rule(
    code: str,
    dimension: str,
    column: str | None,
    *,
    outcome: str = "PASS",
    test_kind: str = "GENERIC",
) -> QualityContractRuleEvaluation:
    return QualityContractRuleEvaluation.model_validate(
        {
            "code": code,
            "label": code.replace("_", " ").title(),
            "quality_dimension": dimension,
            "test_kind": test_kind,
            "column_name": column,
            "outcome": outcome,
            "matched_status": "PASS" if outcome == "PASS" else "FAIL",
            "matched_severity": "ERROR",
            "message": "proof",
        }
    )


def _contract(*, blocked: bool = False) -> QualityContractSummary:
    rules = [
        _rule("OBSERVATION_DATE_REQUIRED", "COMPLETENESS", "observation_date"),
        _rule("RATE_REQUIRED", "COMPLETENESS", "rate", outcome="BLOCK" if blocked else "PASS"),
        _rule("OBSERVATION_DATE_UNIQUE", "UNIQUENESS", "observation_date"),
        _rule("RATE_DIRECTION_VALID", "VALIDITY", "rate_direction"),
        _rule("RATE_REASONABLE", "BUSINESS_RULE", None, test_kind="SINGULAR"),
    ]
    return QualityContractSummary(
        contract_code="FED_FUNDS_RATE_DAILY_QUALITY",
        contract_version="1.1.0",
        contract_name="Federal Funds Rate Daily Quality Contract",
        description="proof",
        target_name="fct_fed_funds_rate_daily",
        layer="MART",
        enforcement_mode="BLOCK",
        artifact_status="READY",
        evidence_trust_posture="BLOCKED" if blocked else "TRUSTED",
        contract_status="BLOCKED" if blocked else "COMPLIANT",
        minimum_pass_rate=1.0,
        pass_rate=0.8 if blocked else 1.0,
        required_rule_count=5,
        satisfied_rule_count=4 if blocked else 5,
        warning_rule_count=0,
        blocking_rule_count=1 if blocked else 0,
        missing_rule_count=0,
        source_path="contracts/quality/fed_funds_rate_daily.v1.json",
        rules=rules,
    )


def _incidents(*, blocked: bool = False) -> QualityIncidentSummary:
    items = []
    if blocked:
        now = datetime.now(UTC)
        items = [
            QualityIncidentRead(
                id="incident-1",
                incident_key="FED_FUNDS_RATE_DAILY_QUALITY:RATE_REQUIRED",
                contract_code="FED_FUNDS_RATE_DAILY_QUALITY",
                contract_version="1.1.0",
                rule_code="RATE_REQUIRED",
                rule_label="Rate Required",
                target_name="fct_fed_funds_rate_daily",
                layer="MART",
                quality_dimension="COMPLETENESS",
                severity="BLOCKING",
                status="OPEN",
                evidence_outcome="BLOCK",
                matched_check_name="mart_rate_present",
                matched_status="FAIL",
                message="rate failed",
                occurrence_count=1,
                first_detected_at=now,
                last_detected_at=now,
                created_at=now,
                updated_at=now,
                events=[],
            )
        ]
    return QualityIncidentSummary(
        contract_code="FED_FUNDS_RATE_DAILY_QUALITY",
        contract_status="BLOCKED" if blocked else "COMPLIANT",
        artifact_status="READY",
        total_count=len(items),
        active_count=len(items),
        open_count=len(items),
        acknowledged_count=0,
        resolved_count=0,
        blocking_active_count=len(items),
        warning_active_count=0,
        incidents=items,
    )


def test_lineage_trust_overlay_maps_clean_quality_to_assets_and_fields() -> None:
    summary = compose_lineage_trust_summary(
        asset_lineage=_asset_lineage(),
        field_lineage=_field_lineage(),
        quality=_quality(),
        contract=_contract(),
        incidents=_incidents(),
    )

    assert summary.artifact_status == "READY"
    assert summary.evidence_trust_posture == "TRUSTED"
    assert summary.contract_status == "COMPLIANT"
    assert summary.check_count == 14
    assert summary.passed_check_count == 14
    assert summary.required_contract_rule_count == 5
    assert summary.satisfied_contract_rule_count == 5
    assert summary.protected_asset_count == 4
    assert summary.protected_field_count == 9
    assert {overlay.quality_status for overlay in summary.overlays} == {"TRUSTED"}


def test_lineage_trust_overlay_maps_blocking_incident_to_mart_asset_and_rate_field() -> None:
    summary = compose_lineage_trust_summary(
        asset_lineage=_asset_lineage(),
        field_lineage=_field_lineage(),
        quality=_quality(status="FAIL"),
        contract=_contract(blocked=True),
        incidents=_incidents(blocked=True),
    )

    mart_asset = next(
        overlay
        for overlay in summary.overlays
        if overlay.scope == "ASSET" and overlay.node_label == "fct_fed_funds_rate_daily"
    )
    mart_rate = next(
        overlay
        for overlay in summary.overlays
        if overlay.scope == "FIELD" and overlay.node_label == "fct_fed_funds_rate_daily.rate"
    )
    assert mart_asset.quality_status == "BLOCKED"
    assert mart_asset.active_incident_count == 1
    assert mart_rate.quality_status == "BLOCKED"
    assert mart_rate.blocking_incident_count == 1


def test_lineage_trust_overlay_contract_rules_do_not_pollute_unrelated_fields() -> None:
    summary = compose_lineage_trust_summary(
        asset_lineage=_asset_lineage(),
        field_lineage=_field_lineage(),
        quality=_quality(),
        contract=_contract(),
        incidents=_incidents(),
    )

    source_rate = next(
        overlay
        for overlay in summary.overlays
        if overlay.scope == "FIELD" and overlay.node_label == "fed_funds_rate.rate"
    )
    mart_date = next(
        overlay
        for overlay in summary.overlays
        if overlay.scope == "FIELD"
        and overlay.node_label == "fct_fed_funds_rate_daily.observation_date"
    )
    assert source_rate.contract_rule_count == 0
    assert mart_date.contract_rule_count == 2


def test_lineage_trust_overlay_is_partial_when_quality_artifacts_are_pending() -> None:
    quality = _quality()
    quality.artifact_status = "PENDING"
    quality.trust_posture = "PENDING"
    contract = _contract()
    contract.artifact_status = "PENDING"
    contract.contract_status = "PENDING"
    for rule in contract.rules:
        rule.outcome = "PENDING"
        rule.matched_status = None

    summary = compose_lineage_trust_summary(
        asset_lineage=_asset_lineage(),
        field_lineage=_field_lineage(),
        quality=quality,
        contract=contract,
        incidents=_incidents(),
    )

    assert summary.artifact_status == "PARTIAL"
    assert summary.evidence_trust_posture == "PENDING"
    assert {overlay.quality_status for overlay in summary.overlays} == {"PENDING"}
