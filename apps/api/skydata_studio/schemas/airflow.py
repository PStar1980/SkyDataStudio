from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class AirflowComponentHealth(BaseModel):
    code: str
    label: str
    status: Literal["HEALTHY", "UNHEALTHY", "UNKNOWN"]
    latest_heartbeat: str | None = None


class AirflowDagSummary(BaseModel):
    dag_id: str
    display_name: str
    description: str | None = None
    paused: bool
    stale: bool
    timetable: str | None = None
    tags: list[str]


class AirflowIntegrationSummary(BaseModel):
    connection_status: Literal["CONNECTED", "DEGRADED", "UNAVAILABLE"]
    api_version: str
    api_base_url: str
    ui_url: str
    auth_mode: str
    dag_count: int
    healthy_components: int
    component_count: int
    components: list[AirflowComponentHealth]
    dags: list[AirflowDagSummary]
    error: str | None = None


class AirflowDagRunSummary(BaseModel):
    dag_id: str
    dag_run_id: str
    state: str
    run_type: str | None = None
    logical_date: datetime | None = None
    queued_at: datetime | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    conf: dict[str, object] = Field(default_factory=dict)


class AirflowDagRunList(BaseModel):
    dag_id: str
    total: int
    items: list[AirflowDagRunSummary]


class AirflowTaskInstanceSummary(BaseModel):
    task_id: str
    task_display_name: str
    state: str
    try_number: int = 0
    map_index: int = -1
    start_date: datetime | None = None
    end_date: datetime | None = None
    duration: float | None = None
    operator: str | None = None


class AirflowDagRunDetail(BaseModel):
    run: AirflowDagRunSummary
    tasks: list[AirflowTaskInstanceSummary]
    task_state_counts: dict[str, int] = Field(default_factory=dict)
    studio_run_key: str | None = None


class AirflowDagRunTriggerRequest(BaseModel):
    pipeline_code: str = Field(default="FED_FUNDS_RATE_PIPELINE", min_length=1, max_length=120)
    version_number: int | None = Field(default=None, ge=1)
    run_date: date | None = None


class AirflowDagRunTriggerResponse(BaseModel):
    run: AirflowDagRunSummary


class AirflowBackfillSummary(BaseModel):
    id: int
    dag_id: str
    from_date: datetime
    to_date: datetime
    is_paused: bool = False
    reprocess_behavior: str
    max_active_runs: int
    run_backwards: bool = False
    created_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None


class AirflowBackfillList(BaseModel):
    dag_id: str
    total: int
    items: list[AirflowBackfillSummary]


class AirflowBackfillCreateRequest(BaseModel):
    pipeline_code: str = Field(default="FED_FUNDS_RATE_PIPELINE", min_length=1, max_length=120)
    version_number: int | None = Field(default=None, ge=1)
    from_date: date
    to_date: date
    reprocess_behavior: Literal["none", "failed", "completed"] = "none"
    max_active_runs: int = Field(default=1, ge=1, le=3)
    run_backwards: bool = False

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.to_date < self.from_date:
            raise ValueError("Backfill to_date must be on or after from_date.")
        if (self.to_date - self.from_date).days > 6:
            raise ValueError("Local proof backfills are limited to a 7-day window.")
        return self


class AirflowBackfillCreateResponse(BaseModel):
    backfill: AirflowBackfillSummary


class AirflowAssetSummary(BaseModel):
    id: int
    uri: str
    name: str | None = None
    group: str | None = None


class AirflowAssetEventSummary(BaseModel):
    id: int
    asset_id: int
    uri: str
    timestamp: datetime | None = None
    extra: dict[str, object] = Field(default_factory=dict)
    created_dag_run_ids: list[str] = Field(default_factory=list)


class AirflowIngestionSourceSummary(BaseModel):
    ingestion_run_id: str
    domain_code: str
    source_code: str
    status_code: str
    terminal: bool
    success_like: bool
    selected_assets: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None


class AirflowIngestionEventPreview(BaseModel):
    dag_id: str
    asset_uri: str
    asset_registered: bool
    eligible: bool
    already_emitted: bool
    ingestion_run: AirflowIngestionSourceSummary | None = None
    event: AirflowAssetEventSummary | None = None
    message: str


class AirflowIngestionEventTriggerRequest(BaseModel):
    ingestion_run_id: str | None = None
    domain_code: str = Field(default="MACRO", min_length=1, max_length=80)
    source_code: str = Field(default="FRED", min_length=1, max_length=80)
    asset_code: str = Field(default="DFF", min_length=1, max_length=120)
    pipeline_code: str = Field(
        default="FED_FUNDS_RATE_PIPELINE",
        min_length=1,
        max_length=120,
    )
    version_number: int | None = Field(default=None, ge=1)


class AirflowIngestionEventTriggerResponse(BaseModel):
    dag_id: str
    asset: AirflowAssetSummary
    event: AirflowAssetEventSummary
    ingestion_run: AirflowIngestionSourceSummary
    reused: bool = False
