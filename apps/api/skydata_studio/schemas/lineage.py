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

LineageTrustStatus = Literal["TRUSTED", "DEGRADED", "BLOCKED", "PENDING"]


class LineageTrustOverlay(BaseModel):
    node_id: str
    node_label: str
    scope: Literal["ASSET", "FIELD"]
    layer: str
    relation: str | None = None
    quality_status: LineageTrustStatus
    check_count: int = Field(ge=0)
    passed_check_count: int = Field(ge=0)
    warning_check_count: int = Field(ge=0)
    failed_check_count: int = Field(ge=0)
    contract_rule_count: int = Field(ge=0)
    satisfied_contract_rule_count: int = Field(ge=0)
    active_incident_count: int = Field(ge=0)
    blocking_incident_count: int = Field(ge=0)
    quality_dimensions: list[str]


class LineageTrustSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 8.3 — Quality and Incident Lineage Overlay Foundation"
    artifact_status: Literal["READY", "PARTIAL", "MISSING"]
    evidence_trust_posture: Literal["TRUSTED", "DEGRADED", "BLOCKED", "PENDING"]
    contract_status: Literal["COMPLIANT", "DEGRADED", "BLOCKED", "PENDING"]
    check_count: int = Field(ge=0)
    passed_check_count: int = Field(ge=0)
    required_contract_rule_count: int = Field(ge=0)
    satisfied_contract_rule_count: int = Field(ge=0)
    active_incident_count: int = Field(ge=0)
    blocking_incident_count: int = Field(ge=0)
    protected_asset_count: int = Field(ge=0)
    protected_field_count: int = Field(ge=0)
    overlays: list[LineageTrustOverlay]


RuntimeLineageNodeType = Literal[
    "STRUCTURAL_ASSET",
    "PIPELINE_DEFINITION",
    "AIRFLOW_DAG",
    "AIRFLOW_DAG_RUN",
    "AIRFLOW_TASK",
    "STUDIO_PIPELINE_RUN",
    "STUDIO_STEP_RUN",
]
RuntimeLineageEdgeType = Literal[
    "READS_FROM",
    "ORCHESTRATED_BY",
    "EXECUTION",
    "TASK_FLOW",
    "CALLS_STUDIO",
    "STEP_FLOW",
    "MATERIALIZES",
]


class RuntimeLineageNode(BaseModel):
    id: str
    label: str
    node_type: RuntimeLineageNodeType
    system: str
    status: str
    relation: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeLineageEdge(BaseModel):
    id: str
    upstream_id: str
    downstream_id: str
    edge_type: RuntimeLineageEdgeType
    label: str


class RuntimeLineageSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 8.4 — Pipeline and Airflow Execution Lineage Foundation"
    runtime_status: Literal["READY", "PARTIAL", "MISSING"]
    airflow_connection_status: Literal["CONNECTED", "UNAVAILABLE", "UNKNOWN"]
    pipeline_code: str
    dag_id: str
    dag_run_id: str | None = None
    studio_run_id: str | None = None
    studio_run_key: str | None = None
    airflow_dag_run_status: str | None = None
    studio_run_status: str | None = None
    airflow_task_count: int = Field(default=0, ge=0)
    successful_airflow_task_count: int = Field(default=0, ge=0)
    studio_step_count: int = Field(default=0, ge=0)
    succeeded_studio_step_count: int = Field(default=0, ge=0)
    replay_count: int = Field(default=0, ge=0)
    materialization_executed: bool = False
    data_mutation_applied: bool = False
    target_relation: str | None = None
    target_row_count: int | None = Field(default=None, ge=0)
    airflow_error: str | None = None
    node_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    nodes: list[RuntimeLineageNode] = Field(default_factory=list)
    edges: list[RuntimeLineageEdge] = Field(default_factory=list)

