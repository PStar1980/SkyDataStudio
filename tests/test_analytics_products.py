from collections.abc import Generator
from typing import Literal

import pytest
from fastapi.testclient import TestClient
from skydata_studio.api.routes import analytics as analytics_route
from skydata_studio.db.session import get_session
from skydata_studio.main import app
from skydata_studio.schemas.analytics import (
    AnalyticsProductDefinition,
    AnalyticsProductSummary,
    AnalyticsRelationEvidence,
)
from skydata_studio.schemas.dbt import (
    DbtModelCatalogueItem,
    DbtModelCatalogueSummary,
    DbtSemanticDimensionSummary,
    DbtSemanticLayerSummary,
    DbtSemanticMetricSummary,
    DbtSemanticModelSummary,
)
from skydata_studio.schemas.lineage import (
    AnalyticsConsumerDefinition,
    AnalyticsConsumerImpactSummary,
    AnalyticsConsumerLineageSummary,
    AnalyticsConsumerNode,
)
from skydata_studio.schemas.quality import QualityContractSummary
from skydata_studio.services.analytics_products import compose_analytics_product_summary
from sqlalchemy.orm import Session

client = TestClient(app)


def _product() -> AnalyticsProductDefinition:
    return AnalyticsProductDefinition(
        code="FED_FUNDS_RATE_DAILY_PRODUCT",
        version="1.0.0",
        name="Federal Funds Rate Daily Analytical Product",
        description="Proof product.",
        owner="SkyData Studio",
        domain="Macroeconomics",
        source_relation="mart.fed_funds_rate",
        mart_relation="dbt_mart.fct_fed_funds_rate_daily",
        freshness_column="observation_date",
        semantic_model="fed_funds_rate_daily",
        quality_contract_code="FED_FUNDS_RATE_DAILY_QUALITY",
        required_metrics=[
            "average_federal_funds_rate",
            "federal_funds_observation_count",
            "maximum_federal_funds_rate",
            "minimum_federal_funds_rate",
        ],
        required_dimensions=[
            "observation_date",
            "observation_month",
            "observation_year",
            "rate_direction",
        ],
        consumer_codes=["FED_FUNDS_RATE_OVERVIEW"],
    )


def _relation(relation: str, rows: int, latest: str) -> AnalyticsRelationEvidence:
    return AnalyticsRelationEvidence(
        relation=relation,
        status="READY",
        row_count=rows,
        max_freshness_value=latest,
    )


def _catalogue(
    status: Literal["READY", "ERROR", "UNKNOWN"] = "READY",
) -> DbtModelCatalogueSummary:
    model = DbtModelCatalogueItem(
        unique_id="model.skydata_studio.fct_fed_funds_rate_daily",
        name="fct_fed_funds_rate_daily",
        layer="MART",
        relation="dbt_mart.fct_fed_funds_rate_daily",
        materialization="TABLE",
        build_status=status,
        path="models/marts/fct_fed_funds_rate_daily.sql",
        tags=[],
        columns=[],
        upstream=[],
        downstream=[],
        test_count=5,
    )
    return DbtModelCatalogueSummary(
        artifact_status="READY",
        model_count=1,
        ready_model_count=1 if status == "READY" else 0,
        source_count=1,
        test_count=5,
        models=[model],
    )


def _semantic() -> DbtSemanticLayerSummary:
    dimensions = [
        DbtSemanticDimensionSummary(
            name="observation_date", dimension_type="TIME", granularity="DAY"
        ),
        DbtSemanticDimensionSummary(
            name="observation_month", dimension_type="TIME", granularity="MONTH"
        ),
        DbtSemanticDimensionSummary(
            name="observation_year", dimension_type="CATEGORICAL"
        ),
        DbtSemanticDimensionSummary(name="rate_direction", dimension_type="CATEGORICAL"),
    ]
    metric_names = [
        "average_federal_funds_rate",
        "federal_funds_observation_count",
        "maximum_federal_funds_rate",
        "minimum_federal_funds_rate",
    ]
    metrics = [
        DbtSemanticMetricSummary(
            unique_id=f"metric.skydata_studio.{name}",
            name=name,
            label=name.replace("_", " ").title(),
            metric_type="SIMPLE",
            semantic_model="fed_funds_rate_daily",
        )
        for name in metric_names
    ]
    model = DbtSemanticModelSummary(
        unique_id="semantic_model.skydata_studio.fed_funds_rate_daily",
        name="fed_funds_rate_daily",
        relation="dbt_mart.fct_fed_funds_rate_daily",
        entities=[],
        dimensions=dimensions,
        metric_names=metric_names,
    )
    return DbtSemanticLayerSummary(
        artifact_status="READY",
        semantic_model_count=1,
        metric_count=4,
        entity_count=0,
        dimension_count=4,
        semantic_models=[model],
        metrics=metrics,
    )


def _quality(
    status: Literal["COMPLIANT", "DEGRADED", "BLOCKED", "PENDING"] = "COMPLIANT",
) -> QualityContractSummary:
    return QualityContractSummary(
        contract_code="FED_FUNDS_RATE_DAILY_QUALITY",
        contract_version="1.1.0",
        contract_name="Federal Funds Rate Daily Quality Contract",
        description="Proof quality contract.",
        target_name="fct_fed_funds_rate_daily",
        layer="MART",
        enforcement_mode="BLOCK",
        artifact_status="READY",
        evidence_trust_posture="TRUSTED",
        contract_status=status,
        minimum_pass_rate=1.0,
        pass_rate=1.0 if status == "COMPLIANT" else 0.8,
        required_rule_count=5,
        satisfied_rule_count=5 if status == "COMPLIANT" else 4,
        warning_rule_count=0,
        blocking_rule_count=0 if status == "COMPLIANT" else 1,
        missing_rule_count=0,
        source_path="contracts/quality/fed_funds_rate_daily.v1.json",
        rules=[],
    )


def _consumers() -> AnalyticsConsumerLineageSummary:
    definition = AnalyticsConsumerDefinition(
        code="FED_FUNDS_RATE_OVERVIEW",
        version="1.0.0",
        name="Federal Funds Rate Overview",
        description="Proof consumer.",
        consumer_type="REPORT",
        delivery_system="POWER_BI",
        deployment_status="DECLARED",
        semantic_model="fed_funds_rate_daily",
        required_metrics=[
            "average_federal_funds_rate",
            "federal_funds_observation_count",
            "maximum_federal_funds_rate",
            "minimum_federal_funds_rate",
        ],
        required_dimensions=[
            "observation_date",
            "observation_month",
            "observation_year",
            "rate_direction",
        ],
        owner="SkyData Studio",
    )
    node = AnalyticsConsumerNode(
        id="consumer:fed_funds_rate_overview",
        label="Federal Funds Rate Overview",
        node_type="ANALYTICS_CONSUMER",
        system="POWER_BI",
        status="READY",
        metadata={"consumer_code": "FED_FUNDS_RATE_OVERVIEW"},
    )
    return AnalyticsConsumerLineageSummary(
        consumer_status="READY",
        semantic_artifact_status="READY",
        consumer_contract_count=1,
        resolved_consumer_count=1,
        declared_metric_count=4,
        resolved_metric_count=4,
        unresolved_metric_count=0,
        node_count=1,
        edge_count=0,
        source_paths=[],
        consumers=[definition],
        metric_bindings=[],
        nodes=[node],
        edges=[],
        default_impact=AnalyticsConsumerImpactSummary(),
    )


def _summary(
    *,
    source_rows: int = 26340,
    mart_rows: int = 26340,
    quality_status: Literal["COMPLIANT", "DEGRADED", "BLOCKED", "PENDING"] = "COMPLIANT",
) -> AnalyticsProductSummary:
    return compose_analytics_product_summary(
        product=_product(),
        source_path="contracts/analytics/products/fed_funds_rate_daily_product.v1.json",
        source=_relation("mart.fed_funds_rate", source_rows, "2026-08-13"),
        mart=_relation("dbt_mart.fct_fed_funds_rate_daily", mart_rows, "2026-08-13"),
        catalogue=_catalogue(),
        semantic=_semantic(),
        quality=_quality(quality_status),
        consumers=_consumers(),
    )


def test_analytical_product_is_ready_when_all_publication_gates_pass() -> None:
    summary = _summary()

    assert summary.product_status == "READY"
    assert summary.freshness_status == "ALIGNED"
    assert summary.row_count_delta == 0
    assert summary.resolved_metric_count == 4
    assert summary.resolved_consumer_count == 1
    assert all(gate.status == "PASS" for gate in summary.gates)


def test_analytical_product_is_stale_when_curated_source_is_ahead() -> None:
    summary = _summary(source_rows=26340, mart_rows=26335)

    assert summary.product_status == "STALE"
    assert summary.freshness_status == "STALE"
    assert summary.refresh_required is True
    assert summary.row_count_delta == 5
    freshness_gate = next(gate for gate in summary.gates if gate.code == "FRESHNESS_ALIGNMENT")
    assert freshness_gate.status == "BLOCK"


def test_analytical_product_is_blocked_by_noncompliant_quality_contract() -> None:
    summary = _summary(quality_status="BLOCKED")

    assert summary.product_status == "BLOCKED"
    quality_gate = next(gate for gate in summary.gates if gate.code == "QUALITY_CONTRACT")
    assert quality_gate.status == "BLOCK"


def test_analytics_product_endpoint_projects_service_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _summary()

    def fake_summary(session: Session) -> AnalyticsProductSummary:
        del session
        return expected

    def override_session() -> Generator[Session, None, None]:
        with Session() as session:
            yield session

    monkeypatch.setattr(analytics_route, "analytics_product_summary", fake_summary)
    app.dependency_overrides[get_session] = override_session
    try:
        response = client.get("/api/v1/analytics/products/summary")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_status"] == "READY"
    assert payload["freshness_status"] == "ALIGNED"
    assert payload["resolved_metric_count"] == 4
