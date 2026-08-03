from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConsumerContract(BaseModel):
    code: str
    purpose: str
    direction: Literal["SKYCOMMAND_TO_SKYDATA"] = "SKYCOMMAND_TO_SKYDATA"
    access: Literal["READ_ONLY"] = "READ_ONLY"


class IngestionRunTotals(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items_requested: int = Field(default=0, alias="itemsRequested")
    items_succeeded: int = Field(default=0, alias="itemsSucceeded")
    items_failed: int = Field(default=0, alias="itemsFailed")
    rows_staged: int = Field(default=0, alias="rowsStaged")
    rows_inserted: int = Field(default=0, alias="rowsInserted")
    rows_updated: int = Field(default=0, alias="rowsUpdated")
    rows_rejected: int = Field(default=0, alias="rowsRejected")
    quality_issue_count: int = Field(default=0, alias="qualityIssueCount")
    quality_status_code: Literal["PASS", "WARN", "FAIL"] = Field(
        default="PASS", alias="qualityStatusCode"
    )


class IngestionRunItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset_code: str = Field(alias="assetCode")
    attempt_number: int = Field(default=1, alias="attemptNumber")
    outcome: Literal["UPDATED", "UNCHANGED", "FAILED", "SKIPPED", "REJECTED", "CANCELLED"]
    source_max_date: str | None = Field(default=None, alias="sourceMaxDate")
    current_target_max_date: str | None = Field(default=None, alias="currentTargetMaxDate")
    rows_inserted: int = Field(default=0, alias="rowsInserted")
    rows_updated: int = Field(default=0, alias="rowsUpdated")
    rows_rejected: int = Field(default=0, alias="rowsRejected")
    quality_issue_count: int = Field(default=0, alias="qualityIssueCount")
    quality_status_code: Literal["PASS", "WARN", "FAIL"] = Field(
        default="PASS", alias="qualityStatusCode"
    )
    error_code: str | None = Field(default=None, alias="errorCode")
    error_message: str | None = Field(default=None, alias="errorMessage")
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionRunSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ingestion_run_id: str | None = Field(default=None, alias="ingestionRunId")
    domain_code: str = Field(alias="domainCode")
    source_code: str = Field(alias="sourceCode")
    mode_code: str = Field(alias="modeCode")
    trigger_code: str = Field(alias="triggerCode")
    outcome: Literal["SUCCESS", "PARTIAL", "FAILED", "CANCELLED"]
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime = Field(alias="completedAt")
    duration_ms: int = Field(default=0, alias="durationMs")
    totals: IngestionRunTotals
    items: list[IngestionRunItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
