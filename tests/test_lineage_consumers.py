from skydata_studio.schemas.dbt import (
    DbtSemanticDimensionSummary,
    DbtSemanticLayerSummary,
    DbtSemanticMetricSummary,
    DbtSemanticModelSummary,
)
from skydata_studio.schemas.lineage import AnalyticsConsumerDefinition
from skydata_studio.services.lineage_consumers import compose_consumer_lineage_summary


def _semantic() -> DbtSemanticLayerSummary:
    metrics = [
        DbtSemanticMetricSummary(
            unique_id=f"metric.skydata_studio.{name}",
            name=name,
            label=label,
            metric_type="SIMPLE",
            semantic_model="fed_funds_rate_daily",
        )
        for name, label in [
            ("average_federal_funds_rate", "Average Federal Funds Rate"),
            ("federal_funds_observation_count", "Federal Funds Observation Count"),
            ("maximum_federal_funds_rate", "Maximum Federal Funds Rate"),
            ("minimum_federal_funds_rate", "Minimum Federal Funds Rate"),
        ]
    ]
    dimensions = [
        DbtSemanticDimensionSummary(
            name=name,
            dimension_type=(
                "TIME"
                if name.startswith("observation_") and name != "observation_year"
                else "CATEGORICAL"
            ),
            granularity=(
                "DAY"
                if name == "observation_date"
                else "MONTH" if name == "observation_month" else None
            ),
        )
        for name in [
            "observation_date",
            "observation_month",
            "observation_year",
            "rate_direction",
        ]
    ]
    model = DbtSemanticModelSummary(
        unique_id="semantic_model.skydata_studio.fed_funds_rate_daily",
        name="fed_funds_rate_daily",
        relation="dbt_mart.fct_fed_funds_rate_daily",
        entities=[],
        dimensions=dimensions,
        metric_names=[metric.name for metric in metrics],
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


def _consumer(*, metrics: list[str] | None = None) -> AnalyticsConsumerDefinition:
    return AnalyticsConsumerDefinition(
        code="FED_FUNDS_RATE_OVERVIEW",
        version="1.0.0",
        name="Federal Funds Rate Overview",
        description="Proof report consumer.",
        consumer_type="REPORT",
        delivery_system="POWER_BI",
        deployment_status="DECLARED",
        semantic_model="fed_funds_rate_daily",
        required_metrics=metrics or [
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


def test_consumer_lineage_resolves_declared_metrics() -> None:
    summary = compose_consumer_lineage_summary(
        consumers=[_consumer()],
        semantic=_semantic(),
        source_paths=["contracts/analytics/fed_funds_rate_overview.v1.json"],
    )

    assert summary.consumer_status == "READY"
    assert summary.consumer_contract_count == 1
    assert summary.resolved_consumer_count == 1
    assert summary.declared_metric_count == 4
    assert summary.resolved_metric_count == 4
    assert summary.unresolved_metric_count == 0
    assert summary.node_count == 5
    assert summary.edge_count == 4


def test_consumer_lineage_reports_missing_metric_without_fabricating_edge() -> None:
    summary = compose_consumer_lineage_summary(
        consumers=[_consumer(metrics=["average_federal_funds_rate", "missing_metric"])],
        semantic=_semantic(),
    )

    assert summary.consumer_status == "PARTIAL"
    assert summary.resolved_consumer_count == 0
    assert summary.declared_metric_count == 2
    assert summary.resolved_metric_count == 1
    assert summary.unresolved_metric_count == 1
    assert summary.edge_count == 1
    missing = next(binding for binding in summary.metric_bindings if not binding.resolved)
    assert missing.metric_name == "missing_metric"


def test_consumer_lineage_metric_impact_reaches_declared_report() -> None:
    summary = compose_consumer_lineage_summary(
        consumers=[_consumer()],
        semantic=_semantic(),
        focus_metric_name="average_federal_funds_rate",
    )

    assert summary.default_impact.selected_metric_name == "average_federal_funds_rate"
    assert summary.default_impact.downstream_consumer_count == 1
    assert summary.default_impact.consumers[0].label == "Federal Funds Rate Overview"
    assert summary.default_impact.consumers[0].system == "POWER_BI"


def test_consumer_lineage_declaration_does_not_claim_power_bi_deployment() -> None:
    summary = compose_consumer_lineage_summary(
        consumers=[_consumer()],
        semantic=_semantic(),
    )

    report = next(node for node in summary.nodes if node.node_type == "ANALYTICS_CONSUMER")
    assert report.status == "READY"
    assert report.metadata["deployment_status"] == "DECLARED"
