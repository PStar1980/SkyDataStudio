from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


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
