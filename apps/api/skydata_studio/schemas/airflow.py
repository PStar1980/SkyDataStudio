from typing import Literal

from pydantic import BaseModel


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
