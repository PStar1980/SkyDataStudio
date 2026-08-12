from typing import Literal

from pydantic import BaseModel, Field


class DbtQualityCheckSummary(BaseModel):
    unique_id: str
    name: str
    test_kind: Literal["GENERIC", "SINGULAR"]
    quality_dimension: Literal[
        "COMPLETENESS",
        "UNIQUENESS",
        "VALIDITY",
        "REFERENTIAL_INTEGRITY",
        "BUSINESS_RULE",
        "OTHER",
    ]
    target_name: str
    target_resource_type: Literal["MODEL", "SOURCE", "UNKNOWN"]
    layer: Literal["SOURCE", "STAGING", "INTERMEDIATE", "MART", "UNKNOWN"]
    column_name: str | None = None
    severity: Literal["ERROR", "WARN"]
    status: Literal["PASS", "WARN", "FAIL", "ERROR", "SKIP", "UNKNOWN"]
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
