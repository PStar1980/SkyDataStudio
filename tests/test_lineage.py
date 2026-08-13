from collections.abc import Generator

import pytest
from skydata_studio.db.base import Base
from skydata_studio.schemas.dbt import (
    DbtModelCatalogueItem,
    DbtModelCatalogueSummary,
    DbtModelColumnSummary,
    DbtModelDependencySummary,
    DbtSemanticLayerSummary,
    DbtSemanticMetricSummary,
    DbtSemanticModelSummary,
)
from skydata_studio.schemas.metadata import MetadataAssetCreate, MetadataMappingCreate
from skydata_studio.services.lineage import (
    compose_field_lineage_summary,
    compose_lineage_summary,
)
from skydata_studio.services.metadata_registry import (
    create_metadata_mapping,
    register_metadata_asset,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def lineage_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _asset(*, code: str, layer: str, system: str) -> MetadataAssetCreate:
    return MetadataAssetCreate.model_validate(
        {
            "domain": {"code": "MACRO", "name": "Macroeconomic Data"},
            "system": {"code": system, "name": system.title()},
            "namespace": {"code": layer, "name": layer.title()},
            "code": code,
            "name": code.replace("_", " ").title(),
            "asset_type": "TABLE",
            "layer": layer,
        }
    )


def _register_proof_mapping(session: Session) -> None:
    source = register_metadata_asset(
        session,
        _asset(code="DFF", layer="RAW", system="SKYCOMMAND"),
    )
    target = register_metadata_asset(
        session,
        _asset(code="FED_FUNDS_RATE_MART", layer="MART", system="SKYDATA"),
    )
    create_metadata_mapping(
        session,
        MetadataMappingCreate.model_validate(
            {
                "code": "MAP_DFF_TO_FED_FUNDS_RATE_MART",
                "name": "DFF to Federal Funds Rate Mart",
                "source_asset_id": source.id,
                "target_asset_id": target.id,
                "mapping_type": "TRANSFORM",
                "load_strategy": "MERGE",
                "status": "READY",
                "field_mappings": [
                    {
                        "source_field_code": "OBSERVATION_DATE",
                        "target_field_code": "OBSERVATION_DATE",
                        "target_data_type": "DATE",
                    },
                    {
                        "source_field_code": "VALUE",
                        "target_field_code": "RATE",
                        "target_data_type": "NUMERIC",
                        "transformation_type": "CAST",
                    },
                ],
            }
        ),
    )


def _catalogue() -> DbtModelCatalogueSummary:
    source = DbtModelDependencySummary(
        unique_id="source.skydata_studio.studio_curated.fed_funds_rate",
        name="fed_funds_rate",
        resource_type="SOURCE",
    )
    staging = DbtModelDependencySummary(
        unique_id="model.skydata_studio.stg_fed_funds_rate",
        name="stg_fed_funds_rate",
        resource_type="MODEL",
    )
    intermediate = DbtModelDependencySummary(
        unique_id="model.skydata_studio.int_fed_funds_rate_changes",
        name="int_fed_funds_rate_changes",
        resource_type="MODEL",
    )
    models = [
        DbtModelCatalogueItem(
            unique_id=staging.unique_id,
            name=staging.name,
            layer="STAGING",
            relation="dbt_staging.stg_fed_funds_rate",
            materialization="VIEW",
            build_status="READY",
            path="models/staging/stg_fed_funds_rate.sql",
            tags=[],
            columns=[],
            upstream=[source],
            downstream=[intermediate],
            test_count=3,
        ),
        DbtModelCatalogueItem(
            unique_id=intermediate.unique_id,
            name=intermediate.name,
            layer="INTERMEDIATE",
            relation="dbt_intermediate.int_fed_funds_rate_changes",
            materialization="VIEW",
            build_status="READY",
            path="models/intermediate/int_fed_funds_rate_changes.sql",
            tags=[],
            columns=[],
            upstream=[staging],
            downstream=[
                DbtModelDependencySummary(
                    unique_id="model.skydata_studio.fct_fed_funds_rate_daily",
                    name="fct_fed_funds_rate_daily",
                    resource_type="MODEL",
                )
            ],
            test_count=3,
        ),
        DbtModelCatalogueItem(
            unique_id="model.skydata_studio.fct_fed_funds_rate_daily",
            name="fct_fed_funds_rate_daily",
            layer="MART",
            relation="dbt_mart.fct_fed_funds_rate_daily",
            materialization="TABLE",
            build_status="READY",
            path="models/marts/fct_fed_funds_rate_daily.sql",
            tags=[],
            columns=[],
            upstream=[intermediate],
            downstream=[],
            test_count=5,
        ),
    ]
    return DbtModelCatalogueSummary(
        artifact_status="READY",
        model_count=3,
        ready_model_count=3,
        source_count=1,
        test_count=14,
        models=models,
    )


def _semantic() -> DbtSemanticLayerSummary:
    semantic_name = "fed_funds_rate_daily"
    semantic_model = DbtSemanticModelSummary(
        unique_id="semantic_model.skydata_studio.fed_funds_rate_daily",
        name=semantic_name,
        relation="dbt_mart.fct_fed_funds_rate_daily",
        entities=[],
        dimensions=[],
        metric_names=["average_federal_funds_rate", "maximum_federal_funds_rate"],
    )
    metrics = [
        DbtSemanticMetricSummary(
            unique_id="metric.skydata_studio.average_federal_funds_rate",
            name="average_federal_funds_rate",
            label="Average Federal Funds Rate",
            metric_type="SIMPLE",
            semantic_model=semantic_name,
        ),
        DbtSemanticMetricSummary(
            unique_id="metric.skydata_studio.maximum_federal_funds_rate",
            name="maximum_federal_funds_rate",
            label="Maximum Federal Funds Rate",
            metric_type="SIMPLE",
            semantic_model=semantic_name,
        ),
    ]
    return DbtSemanticLayerSummary(
        artifact_status="READY",
        semantic_model_count=1,
        metric_count=2,
        entity_count=0,
        dimension_count=0,
        semantic_models=[semantic_model],
        metrics=metrics,
    )


def test_lineage_stitches_metadata_dbt_and_semantic_graph(lineage_session: Session) -> None:
    _register_proof_mapping(lineage_session)

    summary = compose_lineage_summary(
        lineage_session,
        catalogue=_catalogue(),
        semantic=_semantic(),
    )

    assert summary.artifact_status == "READY"
    assert summary.metadata_mapping_count == 1
    assert summary.dbt_model_count == 3
    assert summary.semantic_model_count == 1
    assert summary.metric_count == 2
    assert summary.node_count == 9
    assert summary.edge_count == 8
    assert {edge.edge_type for edge in summary.edges} >= {
        "MAPPING",
        "PUBLISHES_AS",
        "DEPENDS_ON",
        "SEMANTIC_OF",
        "METRIC_OF",
    }


def test_lineage_default_impact_walks_from_registered_source(lineage_session: Session) -> None:
    _register_proof_mapping(lineage_session)

    summary = compose_lineage_summary(
        lineage_session,
        catalogue=_catalogue(),
        semantic=_semantic(),
    )

    impact = summary.default_impact
    assert impact.selected_node_label == "DFF"
    assert impact.downstream_node_count == 8
    assert impact.affected_model_count == 3
    assert impact.affected_semantic_model_count == 1
    assert impact.affected_metric_count == 2
    assert impact.affected_layers == [
        "INTERMEDIATE",
        "MART",
        "METRIC",
        "SEMANTIC",
        "SOURCE",
        "STAGING",
    ]


def test_lineage_focus_limits_impact_to_selected_model(lineage_session: Session) -> None:
    _register_proof_mapping(lineage_session)
    model_id = "dbt:model.skydata_studio.int_fed_funds_rate_changes"

    summary = compose_lineage_summary(
        lineage_session,
        catalogue=_catalogue(),
        semantic=_semantic(),
        focus_node_id=model_id,
    )

    impact = summary.default_impact
    assert impact.selected_node_id == model_id
    assert impact.affected_model_count == 1
    assert impact.affected_semantic_model_count == 1
    assert impact.affected_metric_count == 2
    assert {node.label for node in impact.nodes} == {
        "fct_fed_funds_rate_daily",
        "fed_funds_rate_daily",
        "Average Federal Funds Rate",
        "Maximum Federal Funds Rate",
    }


def test_lineage_metadata_only_state_is_partial(lineage_session: Session) -> None:
    _register_proof_mapping(lineage_session)
    missing_catalogue = DbtModelCatalogueSummary(
        artifact_status="MISSING",
        model_count=0,
        ready_model_count=0,
        source_count=0,
        test_count=0,
        models=[],
    )
    missing_semantic = DbtSemanticLayerSummary(
        artifact_status="MISSING",
        semantic_model_count=0,
        metric_count=0,
        entity_count=0,
        dimension_count=0,
        semantic_models=[],
        metrics=[],
    )

    summary = compose_lineage_summary(
        lineage_session,
        catalogue=missing_catalogue,
        semantic=missing_semantic,
    )

    assert summary.artifact_status == "PARTIAL"
    assert summary.node_count == 2
    assert summary.edge_count == 1
    assert summary.default_impact.downstream_node_count == 1


def _field_catalogue() -> DbtModelCatalogueSummary:
    source = DbtModelDependencySummary(
        unique_id="source.skydata_studio.studio_curated.fed_funds_rate",
        name="fed_funds_rate",
        resource_type="SOURCE",
    )
    staging = DbtModelDependencySummary(
        unique_id="model.skydata_studio.stg_fed_funds_rate",
        name="stg_fed_funds_rate",
        resource_type="MODEL",
    )
    intermediate = DbtModelDependencySummary(
        unique_id="model.skydata_studio.int_fed_funds_rate_changes",
        name="int_fed_funds_rate_changes",
        resource_type="MODEL",
    )
    mart = DbtModelDependencySummary(
        unique_id="model.skydata_studio.fct_fed_funds_rate_daily",
        name="fct_fed_funds_rate_daily",
        resource_type="MODEL",
    )
    models = [
        DbtModelCatalogueItem(
            unique_id=staging.unique_id,
            name=staging.name,
            layer="STAGING",
            relation="dbt_staging.stg_fed_funds_rate",
            materialization="VIEW",
            build_status="READY",
            path="models/staging/stg_fed_funds_rate.sql",
            tags=[],
            columns=[
                DbtModelColumnSummary(
                    name="observation_date",
                    lineage_inputs=["source:fed_funds_rate.observation_date"],
                ),
                DbtModelColumnSummary(
                    name="rate",
                    lineage_inputs=["source:fed_funds_rate.rate"],
                ),
            ],
            upstream=[source],
            downstream=[intermediate],
            test_count=3,
        ),
        DbtModelCatalogueItem(
            unique_id=intermediate.unique_id,
            name=intermediate.name,
            layer="INTERMEDIATE",
            relation="dbt_intermediate.int_fed_funds_rate_changes",
            materialization="VIEW",
            build_status="READY",
            path="models/intermediate/int_fed_funds_rate_changes.sql",
            tags=[],
            columns=[
                DbtModelColumnSummary(
                    name="observation_date",
                    lineage_inputs=["model:stg_fed_funds_rate.observation_date"],
                ),
                DbtModelColumnSummary(
                    name="observation_month",
                    lineage_inputs=["model:stg_fed_funds_rate.observation_date"],
                ),
                DbtModelColumnSummary(
                    name="observation_year",
                    lineage_inputs=["model:stg_fed_funds_rate.observation_date"],
                ),
                DbtModelColumnSummary(
                    name="rate",
                    lineage_inputs=["model:stg_fed_funds_rate.rate"],
                ),
                DbtModelColumnSummary(
                    name="previous_rate",
                    lineage_inputs=["model:stg_fed_funds_rate.rate"],
                ),
                DbtModelColumnSummary(
                    name="rate_change",
                    lineage_inputs=["model:stg_fed_funds_rate.rate"],
                ),
                DbtModelColumnSummary(
                    name="rate_change_bps",
                    lineage_inputs=["model:stg_fed_funds_rate.rate"],
                ),
            ],
            upstream=[staging],
            downstream=[mart],
            test_count=3,
        ),
        DbtModelCatalogueItem(
            unique_id=mart.unique_id,
            name=mart.name,
            layer="MART",
            relation="dbt_mart.fct_fed_funds_rate_daily",
            materialization="TABLE",
            build_status="READY",
            path="models/marts/fct_fed_funds_rate_daily.sql",
            tags=[],
            columns=[
                DbtModelColumnSummary(
                    name="observation_key",
                    lineage_inputs=["model:int_fed_funds_rate_changes.observation_date"],
                ),
                DbtModelColumnSummary(
                    name="observation_date",
                    lineage_inputs=["model:int_fed_funds_rate_changes.observation_date"],
                ),
                DbtModelColumnSummary(
                    name="observation_month",
                    lineage_inputs=["model:int_fed_funds_rate_changes.observation_month"],
                ),
                DbtModelColumnSummary(
                    name="observation_year",
                    lineage_inputs=["model:int_fed_funds_rate_changes.observation_year"],
                ),
                DbtModelColumnSummary(
                    name="rate",
                    lineage_inputs=["model:int_fed_funds_rate_changes.rate"],
                ),
                DbtModelColumnSummary(
                    name="previous_rate",
                    lineage_inputs=["model:int_fed_funds_rate_changes.previous_rate"],
                ),
                DbtModelColumnSummary(
                    name="rate_change",
                    lineage_inputs=["model:int_fed_funds_rate_changes.rate_change"],
                ),
                DbtModelColumnSummary(
                    name="rate_change_bps",
                    lineage_inputs=["model:int_fed_funds_rate_changes.rate_change_bps"],
                ),
                DbtModelColumnSummary(
                    name="rate_direction",
                    lineage_inputs=[
                        "model:int_fed_funds_rate_changes.rate",
                        "model:int_fed_funds_rate_changes.previous_rate",
                    ],
                ),
            ],
            upstream=[intermediate],
            downstream=[],
            test_count=5,
        ),
    ]
    return DbtModelCatalogueSummary(
        artifact_status="READY",
        model_count=3,
        ready_model_count=3,
        source_count=1,
        test_count=14,
        models=models,
    )


def _field_semantic() -> DbtSemanticLayerSummary:
    semantic_name = "fed_funds_rate_daily"
    semantic_model = DbtSemanticModelSummary(
        unique_id="semantic_model.skydata_studio.fed_funds_rate_daily",
        name=semantic_name,
        relation="dbt_mart.fct_fed_funds_rate_daily",
        entities=[],
        dimensions=[],
        metric_names=[
            "average_federal_funds_rate",
            "minimum_federal_funds_rate",
            "maximum_federal_funds_rate",
            "federal_funds_observation_count",
        ],
    )
    metrics = [
        DbtSemanticMetricSummary(
            unique_id="metric.skydata_studio.average_federal_funds_rate",
            name="average_federal_funds_rate",
            label="Average Federal Funds Rate",
            metric_type="SIMPLE",
            aggregation="AVERAGE",
            expression="rate",
            semantic_model=semantic_name,
        ),
        DbtSemanticMetricSummary(
            unique_id="metric.skydata_studio.minimum_federal_funds_rate",
            name="minimum_federal_funds_rate",
            label="Minimum Federal Funds Rate",
            metric_type="SIMPLE",
            aggregation="MIN",
            expression="rate",
            semantic_model=semantic_name,
        ),
        DbtSemanticMetricSummary(
            unique_id="metric.skydata_studio.maximum_federal_funds_rate",
            name="maximum_federal_funds_rate",
            label="Maximum Federal Funds Rate",
            metric_type="SIMPLE",
            aggregation="MAX",
            expression="rate",
            semantic_model=semantic_name,
        ),
        DbtSemanticMetricSummary(
            unique_id="metric.skydata_studio.federal_funds_observation_count",
            name="federal_funds_observation_count",
            label="Federal Funds Observation Count",
            metric_type="SIMPLE",
            aggregation="COUNT_DISTINCT",
            expression="observation_key",
            semantic_model=semantic_name,
        ),
    ]
    return DbtSemanticLayerSummary(
        artifact_status="READY",
        semantic_model_count=1,
        metric_count=4,
        entity_count=0,
        dimension_count=0,
        semantic_models=[semantic_model],
        metrics=metrics,
    )


def test_field_lineage_composes_mapping_dbt_columns_and_metrics(
    lineage_session: Session,
) -> None:
    _register_proof_mapping(lineage_session)
    summary = compose_field_lineage_summary(
        lineage_session,
        catalogue=_field_catalogue(),
        semantic=_field_semantic(),
    )
    assert summary.artifact_status == "READY"
    assert summary.field_mapping_count == 2
    assert summary.dbt_annotated_column_count == 18
    assert summary.metric_binding_count == 4
    assert summary.node_count == 28
    assert summary.edge_count == 27


def test_field_lineage_value_impact_reaches_three_rate_metrics(
    lineage_session: Session,
) -> None:
    _register_proof_mapping(lineage_session)
    summary = compose_field_lineage_summary(
        lineage_session,
        catalogue=_field_catalogue(),
        semantic=_field_semantic(),
    )
    value_node = next(node for node in summary.nodes if node.label == "DFF.value")
    focused = compose_field_lineage_summary(
        lineage_session,
        catalogue=_field_catalogue(),
        semantic=_field_semantic(),
        focus_field_id=value_node.id,
    )
    impact = focused.default_impact
    assert impact.downstream_node_count == 15
    assert impact.affected_metric_count == 3
    labels = {node.label for node in impact.nodes}
    assert "fct_fed_funds_rate_daily.rate_direction" in labels
    assert "Federal Funds Observation Count" not in labels


def test_field_lineage_date_impact_reaches_observation_count(
    lineage_session: Session,
) -> None:
    _register_proof_mapping(lineage_session)
    summary = compose_field_lineage_summary(
        lineage_session,
        catalogue=_field_catalogue(),
        semantic=_field_semantic(),
    )
    date_node = next(
        node for node in summary.nodes if node.label == "DFF.observation_date"
    )
    focused = compose_field_lineage_summary(
        lineage_session,
        catalogue=_field_catalogue(),
        semantic=_field_semantic(),
        focus_field_id=date_node.id,
    )
    labels = {node.label for node in focused.default_impact.nodes}
    assert focused.default_impact.affected_metric_count == 1
    assert "Federal Funds Observation Count" in labels
    assert "Average Federal Funds Rate" not in labels


def test_field_lineage_without_dbt_annotations_is_partial(lineage_session: Session) -> None:
    _register_proof_mapping(lineage_session)
    summary = compose_field_lineage_summary(
        lineage_session,
        catalogue=_catalogue(),
        semantic=_semantic(),
    )
    assert summary.artifact_status == "PARTIAL"
    assert summary.field_mapping_count == 2
    assert summary.dbt_annotated_column_count == 0
    assert summary.metric_binding_count == 0
    assert summary.node_count == 6
    assert summary.edge_count == 4
