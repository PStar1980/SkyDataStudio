from typing import Literal

from pydantic import BaseModel, Field

AnalyticsProductStatus = Literal["READY", "STALE", "BLOCKED", "PENDING", "MISSING"]
AnalyticsGateStatus = Literal["PASS", "WARN", "BLOCK", "PENDING"]
AnalyticsFreshnessStatus = Literal["ALIGNED", "STALE", "MISSING", "UNKNOWN"]


class AnalyticsProductDefinition(BaseModel):
    code: str
    version: str
    name: str
    description: str
    owner: str
    domain: str
    source_relation: str
    mart_relation: str
    freshness_column: str
    row_alignment: Literal["EXACT"] = "EXACT"
    semantic_model: str
    quality_contract_code: str
    required_metrics: list[str]
    required_dimensions: list[str]
    consumer_codes: list[str]
    publication_mode: Literal["GATED"] = "GATED"


class AnalyticsRelationEvidence(BaseModel):
    relation: str
    status: Literal["READY", "MISSING"]
    row_count: int | None = Field(default=None, ge=0)
    max_freshness_value: str | None = None


class AnalyticsPublicationGate(BaseModel):
    code: str
    label: str
    status: AnalyticsGateStatus
    message: str


class AnalyticsProductSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 9.1 — Analytical Mart Publication Readiness and Freshness Gate"
    product_status: AnalyticsProductStatus
    product_code: str
    product_version: str
    product_name: str
    description: str
    owner: str
    domain: str
    source_path: str
    source_relation: AnalyticsRelationEvidence
    mart_relation: AnalyticsRelationEvidence
    row_count_delta: int | None = None
    freshness_status: AnalyticsFreshnessStatus
    refresh_required: bool
    model_build_status: Literal["READY", "ERROR", "UNKNOWN", "MISSING"]
    semantic_artifact_status: Literal["READY", "PENDING", "MISSING"]
    semantic_model_resolved: bool
    quality_contract_status: Literal["COMPLIANT", "DEGRADED", "BLOCKED", "PENDING"]
    required_metric_count: int = Field(ge=0)
    resolved_metric_count: int = Field(ge=0)
    required_consumer_count: int = Field(ge=0)
    resolved_consumer_count: int = Field(ge=0)
    gates: list[AnalyticsPublicationGate]
    publication_message: str
