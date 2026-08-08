from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

type PipelineRunStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED"]
type PipelineStepRunStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "SKIPPED"]
type PipelineReplayMode = Literal["REUSE", "FORCE_NEW"]


class PipelineRunRequest(BaseModel):
    pipeline_id: str
    version_number: int | None = Field(default=None, ge=1)
    parameters: dict[str, object] = Field(default_factory=dict)
    replay_mode: PipelineReplayMode = "REUSE"
    replay_key: str | None = Field(default=None, min_length=1, max_length=160)
    trigger_type: Literal["MANUAL", "TEST"] = "MANUAL"

    @field_validator("replay_key")
    @classmethod
    def normalize_replay_key(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class PipelineStepRunRead(BaseModel):
    id: str
    step_id: str
    step_code: str
    step_name: str
    step_type: str
    execution_order: int
    status: str
    attempt_count: int
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    result: dict[str, object]
    error_message: str | None


class PipelineRunRead(BaseModel):
    id: str
    pipeline_id: str
    pipeline_code: str
    pipeline_name: str
    version_id: str
    version_number: int
    run_key: str
    status: str
    trigger_type: str
    execution_mode: str
    environment: str
    parameters: dict[str, object]
    execution_context: dict[str, object]
    result: dict[str, object]
    replay_count: int
    started_at: datetime | None
    completed_at: datetime | None
    last_replayed_at: datetime | None
    error_message: str | None
    step_count: int
    succeeded_steps: int
    failed_steps: int
    step_runs: list[PipelineStepRunRead]
    created_at: datetime
    updated_at: datetime


class PipelineRunExecutionResponse(BaseModel):
    reused: bool
    run: PipelineRunRead


class PipelineRunList(BaseModel):
    total: int
    items: list[PipelineRunRead]


class PipelineRunSummary(BaseModel):
    runs: int = 0
    step_runs: int = 0
    replayed_runs: int = 0
    statuses: dict[str, int] = Field(default_factory=dict)
    environments: dict[str, int] = Field(default_factory=dict)
