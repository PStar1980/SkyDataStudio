from typing import Literal

from pydantic import BaseModel, Field

QualityDimension = Literal[
    "COMPLETENESS",
    "UNIQUENESS",
    "VALIDITY",
    "REFERENTIAL_INTEGRITY",
    "BUSINESS_RULE",
    "OTHER",
]
QualityLayer = Literal["SOURCE", "STAGING", "INTERMEDIATE", "MART", "UNKNOWN"]
QualityStatus = Literal["PASS", "WARN", "FAIL", "ERROR", "SKIP", "UNKNOWN"]


class DbtQualityCheckSummary(BaseModel):
    unique_id: str
    name: str
    test_kind: Literal["GENERIC", "SINGULAR"]
    quality_dimension: QualityDimension
    target_name: str
    target_resource_type: Literal["MODEL", "SOURCE", "UNKNOWN"]
    layer: QualityLayer
    column_name: str | None = None
    severity: Literal["ERROR", "WARN"]
    status: QualityStatus
    failures: int | None = Field(default=None, ge=0)
    execution_time_ms: float | None = Field(default=None, ge=0)
    message: str | None = None
    path: str


class DbtQualitySummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 7.1 — dbt Quality Evidence and Trust Posture Foundation"
    artifact_status: Literal["READY", "PENDING", "MISSING"]
    trust_posture: Literal["TRUSTED", "DEGRADED", "BLOCKED", "PENDING"]
    generated_at: str | None = None
    dbt_version: str | None = None
    invocation_id: str | None = None
    invocation_command: str | None = None
    elapsed_time_ms: float | None = Field(default=None, ge=0)
    test_count: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    unknown_count: int = Field(ge=0)
    source_test_count: int = Field(ge=0)
    model_test_count: int = Field(ge=0)
    checks: list[DbtQualityCheckSummary]


class QualityContractRuleDefinition(BaseModel):
    code: str
    label: str
    quality_dimension: QualityDimension
    test_kind: Literal["GENERIC", "SINGULAR"]
    column_name: str | None = None
    required_status: Literal["PASS"] = "PASS"


class QualityContractDefinition(BaseModel):
    code: str
    version: str
    name: str
    description: str
    target_name: str
    layer: Literal["STAGING", "INTERMEDIATE", "MART"]
    enforcement_mode: Literal["BLOCK", "ADVISORY"]
    minimum_pass_rate: float = Field(ge=0.0, le=1.0)
    rules: list[QualityContractRuleDefinition]


class QualityContractRuleEvaluation(BaseModel):
    code: str
    label: str
    quality_dimension: QualityDimension
    test_kind: Literal["GENERIC", "SINGULAR"]
    column_name: str | None = None
    required_status: Literal["PASS"] = "PASS"
    outcome: Literal["PASS", "WARN", "BLOCK", "MISSING", "PENDING"]
    matched_check_name: str | None = None
    matched_status: QualityStatus | None = None
    matched_severity: Literal["ERROR", "WARN"] | None = None
    message: str


class QualityContractSummary(BaseModel):
    project_name: str = "skydata_studio"
    phase: str = "Phase 7.2 — Quality Contract Gate and Consumer Compatibility Workbench"
    contract_code: str
    contract_version: str
    contract_name: str
    description: str
    target_name: str
    layer: Literal["STAGING", "INTERMEDIATE", "MART"]
    enforcement_mode: Literal["BLOCK", "ADVISORY"]
    artifact_status: Literal["READY", "PENDING", "MISSING"]
    evidence_trust_posture: Literal["TRUSTED", "DEGRADED", "BLOCKED", "PENDING"]
    contract_status: Literal["COMPLIANT", "DEGRADED", "BLOCKED", "PENDING"]
    minimum_pass_rate: float = Field(ge=0.0, le=1.0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    required_rule_count: int = Field(ge=0)
    satisfied_rule_count: int = Field(ge=0)
    warning_rule_count: int = Field(ge=0)
    blocking_rule_count: int = Field(ge=0)
    missing_rule_count: int = Field(ge=0)
    source_path: str
    rules: list[QualityContractRuleEvaluation]
