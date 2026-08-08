from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

type PipelineStatus = Literal["DRAFT", "READY", "ACTIVE", "RETIRED"]
type PipelineVersionStatus = Literal["DRAFT", "READY", "PUBLISHED", "RETIRED"]
type PipelineStepType = Literal["SQL", "PYTHON", "VALIDATION", "DBT", "PUBLISH"]
type PipelineStepStatus = Literal["DRAFT", "READY", "DISABLED"]
type PipelineParameterType = Literal[
    "STRING",
    "INTEGER",
    "DECIMAL",
    "BOOLEAN",
    "DATE",
    "TIMESTAMP",
    "JSON",
]


def _normalize_code(value: str) -> str:
    return value.strip().upper().replace(" ", "_").replace("-", "_")


class PipelineParameterInput(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=160)
    data_type: PipelineParameterType = "STRING"
    required: bool = False
    default_value: object | None = None
    ordinal_position: int = Field(default=1, ge=1)
    description: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return _normalize_code(value)


class PipelineStepInput(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    step_type: PipelineStepType = "SQL"
    execution_order: int = Field(default=1, ge=1)
    status: PipelineStepStatus = "READY"
    mapping_id: str | None = None
    source_asset_id: str | None = None
    target_asset_id: str | None = None
    sql_text: str | None = None
    script_path: str | None = Field(default=None, max_length=500)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    retry_count: int = Field(default=0, ge=0, le=20)
    continue_on_failure: bool = False
    depends_on_codes: list[str] = Field(default_factory=list, max_length=50)
    configuration: dict[str, object] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return _normalize_code(value)

    @field_validator("depends_on_codes")
    @classmethod
    def normalize_dependencies(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(_normalize_code(item) for item in value if item.strip()))


class PipelineDefinitionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: PipelineStatus = "DRAFT"
    environment: str = Field(default="development", min_length=1, max_length=40)
    execution_mode: Literal["LOCAL"] = "LOCAL"
    mapping_id: str | None = None
    version_status: PipelineVersionStatus = "READY"
    version_notes: str | None = None
    parameters: list[PipelineParameterInput] = Field(default_factory=list, max_length=100)
    steps: list[PipelineStepInput] = Field(min_length=1, max_length=250)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return _normalize_code(value)

    @model_validator(mode="after")
    def validate_step_graph(self) -> "PipelineDefinitionCreate":
        codes = [step.code for step in self.steps]
        if len(codes) != len(set(codes)):
            raise ValueError("Pipeline step codes must be unique within a version.")
        order_values = [step.execution_order for step in self.steps]
        if len(order_values) != len(set(order_values)):
            raise ValueError(
                "Pipeline step execution_order values must be unique within a version."
            )
        known = set(codes)
        for step in self.steps:
            if step.code in step.depends_on_codes:
                raise ValueError(f"Pipeline step {step.code} cannot depend on itself.")
            missing = [code for code in step.depends_on_codes if code not in known]
            if missing:
                raise ValueError(
                    f"Pipeline step {step.code} depends on unknown step code(s): "
                    f"{', '.join(missing)}."
                )
        return self


class PipelineMappingRead(BaseModel):
    id: str
    code: str
    name: str
    source_asset_code: str
    source_asset_name: str
    target_asset_code: str
    target_asset_name: str
    load_strategy: str
    status: str


class PipelineParameterRead(BaseModel):
    id: str
    code: str
    name: str
    data_type: str
    required: bool
    default_value: object | None
    ordinal_position: int
    description: str | None


class PipelineStepDependencyRead(BaseModel):
    id: str
    depends_on_step_id: str
    depends_on_step_code: str
    depends_on_step_name: str
    dependency_condition: str


class PipelineStepRead(BaseModel):
    id: str
    code: str
    name: str
    step_type: str
    execution_order: int
    status: str
    mapping_id: str | None
    source_asset_id: str | None
    target_asset_id: str | None
    sql_text: str | None
    script_path: str | None
    timeout_seconds: int
    retry_count: int
    continue_on_failure: bool
    configuration: dict[str, object]
    dependencies: list[PipelineStepDependencyRead]


class PipelineVersionRead(BaseModel):
    id: str
    version_number: int
    status: str
    notes: str | None
    execution_contract: dict[str, object]
    parameter_count: int
    step_count: int
    parameters: list[PipelineParameterRead]
    steps: list[PipelineStepRead]
    created_at: datetime
    updated_at: datetime


class PipelineListItem(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    status: str
    environment: str
    execution_mode: str
    mapping: PipelineMappingRead | None
    current_version: int
    version_count: int
    parameter_count: int
    step_count: int
    created_at: datetime
    updated_at: datetime


class PipelineDetail(PipelineListItem):
    versions: list[PipelineVersionRead]
    attributes: dict[str, object]


class PipelineList(BaseModel):
    total: int
    items: list[PipelineListItem]


class PipelineSummary(BaseModel):
    pipelines: int = 0
    versions: int = 0
    parameters: int = 0
    steps: int = 0
    dependencies: int = 0
    statuses: dict[str, int] = Field(default_factory=dict)
    environments: dict[str, int] = Field(default_factory=dict)
