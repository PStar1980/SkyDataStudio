from typing import Literal

from pydantic import BaseModel, Field


class DbtRelationSummary(BaseModel):
    name: str
    layer: Literal["SOURCE", "STAGING", "INTERMEDIATE", "MART"]
    relation: str
    materialization: Literal["TABLE", "VIEW", "SOURCE"]
    description: str
    status: Literal["READY", "MISSING"]
    row_count: int | None = Field(default=None, ge=0)


class DbtTransformationSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 6.1 — dbt Runtime and Layered Model Foundation"
    runtime: Literal["DOCKER"] = "DOCKER"
    adapter: Literal["POSTGRES"] = "POSTGRES"
    dbt_core_version: str = "1.12.0"
    dbt_postgres_version: str = "1.11.0"
    source_relation: str = "mart.fed_funds_rate"
    model_count: int
    ready_model_count: int
    test_count: int
    layers_ready: int
    layer_count: int
    relations: list[DbtRelationSummary]


class DbtModelColumnSummary(BaseModel):
    name: str
    description: str | None = None


class DbtModelDependencySummary(BaseModel):
    unique_id: str
    name: str
    resource_type: Literal["MODEL", "SOURCE"]


class DbtModelCatalogueItem(BaseModel):
    unique_id: str
    name: str
    layer: Literal["STAGING", "INTERMEDIATE", "MART"]
    relation: str
    materialization: Literal["TABLE", "VIEW"]
    description: str | None = None
    build_status: Literal["READY", "ERROR", "UNKNOWN"]
    path: str
    tags: list[str]
    columns: list[DbtModelColumnSummary]
    upstream: list[DbtModelDependencySummary]
    downstream: list[DbtModelDependencySummary]
    test_count: int = Field(ge=0)


class DbtModelCatalogueSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 6.2 — dbt Model Catalogue and Artifact Evidence"
    artifact_status: Literal["READY", "MISSING"]
    generated_at: str | None = None
    dbt_version: str | None = None
    model_count: int = Field(ge=0)
    ready_model_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    test_count: int = Field(ge=0)
    models: list[DbtModelCatalogueItem]


class DbtSemanticEntitySummary(BaseModel):
    name: str
    entity_type: Literal["PRIMARY", "UNIQUE", "FOREIGN", "NATURAL"]
    expression: str | None = None
    description: str | None = None


class DbtSemanticDimensionSummary(BaseModel):
    name: str
    dimension_type: Literal["TIME", "CATEGORICAL"]
    expression: str | None = None
    granularity: str | None = None
    description: str | None = None


class DbtSemanticMetricSummary(BaseModel):
    unique_id: str
    name: str
    label: str
    metric_type: Literal["SIMPLE", "RATIO", "CUMULATIVE", "DERIVED", "CONVERSION"]
    description: str | None = None
    aggregation: str | None = None
    expression: str | None = None
    time_dimension: str | None = None
    semantic_model: str | None = None


class DbtSemanticModelSummary(BaseModel):
    unique_id: str
    name: str
    description: str | None = None
    relation: str | None = None
    default_time_dimension: str | None = None
    entities: list[DbtSemanticEntitySummary]
    dimensions: list[DbtSemanticDimensionSummary]
    metric_names: list[str]


class DbtSemanticLayerSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 6.3 — dbt Semantic Model and Governed Metric Foundation"
    artifact_status: Literal["READY", "PENDING", "MISSING"]
    generated_at: str | None = None
    dbt_version: str | None = None
    semantic_model_count: int = Field(ge=0)
    metric_count: int = Field(ge=0)
    entity_count: int = Field(ge=0)
    dimension_count: int = Field(ge=0)
    semantic_models: list[DbtSemanticModelSummary]
    metrics: list[DbtSemanticMetricSummary]
