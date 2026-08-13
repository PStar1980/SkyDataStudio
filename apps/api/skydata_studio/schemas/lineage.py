from typing import Literal

from pydantic import BaseModel, Field

LineageNodeType = Literal[
    "SOURCE_ASSET",
    "CURATED_ASSET",
    "DBT_SOURCE",
    "DBT_MODEL",
    "SEMANTIC_MODEL",
    "METRIC",
]
LineageLayer = Literal[
    "RAW",
    "MART",
    "SOURCE",
    "STAGING",
    "INTERMEDIATE",
    "SEMANTIC",
    "METRIC",
    "UNKNOWN",
]
LineageStatus = Literal["READY", "MISSING", "UNKNOWN"]
LineageEdgeType = Literal[
    "MAPPING",
    "PUBLISHES_AS",
    "DEPENDS_ON",
    "SEMANTIC_OF",
    "METRIC_OF",
]


class LineageNode(BaseModel):
    id: str
    label: str
    node_type: LineageNodeType
    layer: LineageLayer
    system: str
    relation: str | None = None
    description: str | None = None
    status: LineageStatus = "UNKNOWN"
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class LineageEdge(BaseModel):
    id: str
    upstream_id: str
    downstream_id: str
    edge_type: LineageEdgeType
    label: str


class LineageImpactSummary(BaseModel):
    selected_node_id: str | None = None
    selected_node_label: str | None = None
    downstream_node_count: int = Field(ge=0)
    affected_model_count: int = Field(ge=0)
    affected_semantic_model_count: int = Field(ge=0)
    affected_metric_count: int = Field(ge=0)
    affected_layers: list[str]
    nodes: list[LineageNode]


class LineageSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 8.1 — Cross-Layer Lineage Graph and Impact Radius Foundation"
    artifact_status: Literal["READY", "PARTIAL", "MISSING"]
    metadata_mapping_count: int = Field(ge=0)
    dbt_model_count: int = Field(ge=0)
    semantic_model_count: int = Field(ge=0)
    metric_count: int = Field(ge=0)
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    nodes: list[LineageNode]
    edges: list[LineageEdge]
    default_impact: LineageImpactSummary


FieldLineageNodeType = Literal[
    "SOURCE_FIELD",
    "CURATED_FIELD",
    "DBT_SOURCE_FIELD",
    "DBT_MODEL_FIELD",
    "METRIC",
]
FieldLineageEdgeType = Literal[
    "FIELD_MAPPING",
    "PUBLISHES_AS",
    "DERIVES",
    "FEEDS_METRIC",
]


class FieldLineageNode(BaseModel):
    id: str
    label: str
    field_name: str
    node_type: FieldLineageNodeType
    layer: LineageLayer
    system: str
    relation: str | None = None
    parent_node_id: str | None = None
    parent_label: str | None = None
    description: str | None = None
    status: LineageStatus = "UNKNOWN"
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class FieldLineageEdge(BaseModel):
    id: str
    upstream_id: str
    downstream_id: str
    edge_type: FieldLineageEdgeType
    label: str


class FieldLineageImpactSummary(BaseModel):
    selected_field_id: str | None = None
    selected_field_label: str | None = None
    downstream_node_count: int = Field(ge=0)
    affected_field_count: int = Field(ge=0)
    affected_metric_count: int = Field(ge=0)
    affected_relations: list[str]
    affected_layers: list[str]
    nodes: list[FieldLineageNode]


class FieldLineageSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 8.2 — Field-Level Lineage and Column Impact Foundation"
    artifact_status: Literal["READY", "PARTIAL", "MISSING"]
    field_mapping_count: int = Field(ge=0)
    dbt_annotated_column_count: int = Field(ge=0)
    metric_binding_count: int = Field(ge=0)
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    nodes: list[FieldLineageNode]
    edges: list[FieldLineageEdge]
    default_impact: FieldLineageImpactSummary
