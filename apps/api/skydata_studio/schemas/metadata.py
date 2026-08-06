from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

type MetadataLayer = Literal["RAW", "STAGING", "INTERMEDIATE", "MART", "SEMANTIC", "REPORT"]
type MetadataAssetType = Literal[
    "TABLE",
    "VIEW",
    "FILE",
    "API",
    "MODEL",
    "DATASET",
    "REPORT",
    "TIME_SERIES",
]
type MetadataSystemType = Literal[
    "APPLICATION",
    "SOURCE",
    "TRANSFORMATION",
    "WAREHOUSE",
    "BI",
]
type MetadataClassification = Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]


def _normalize_code(value: str) -> str:
    return value.strip().upper().replace(" ", "_")


class MetadataReferenceInput(BaseModel):
    code: str = Field(min_length=1, max_length=96)
    name: str | None = Field(default=None, max_length=160)
    description: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return _normalize_code(value)


class MetadataFieldInput(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    name: str | None = Field(default=None, max_length=160)
    data_type: str = Field(min_length=1, max_length=80)
    ordinal_position: int = Field(default=1, ge=1)
    nullable: bool = True
    key_field: bool = False
    classification: MetadataClassification | None = None
    description: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return _normalize_code(value)


class MetadataAssetCreate(BaseModel):
    domain: MetadataReferenceInput
    system: MetadataReferenceInput
    namespace: MetadataReferenceInput
    code: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    system_type: MetadataSystemType = "APPLICATION"
    namespace_type: str = Field(default="SCHEMA", max_length=40)
    physical_namespace: str | None = Field(default=None, max_length=255)
    asset_type: MetadataAssetType = "TABLE"
    layer: MetadataLayer = "RAW"
    physical_name: str | None = Field(default=None, max_length=255)
    owner_name: str | None = Field(default=None, max_length=160)
    owner_email: str | None = Field(default=None, max_length=255)
    classification: MetadataClassification = "INTERNAL"
    criticality: str = Field(default="STANDARD", max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=25)
    fields: list[MetadataFieldInput] = Field(default_factory=list, max_length=250)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return _normalize_code(value)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return sorted({item.strip().lower() for item in value if item.strip()})


class MetadataDomainRead(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    active: bool


class MetadataSystemRead(BaseModel):
    id: str
    code: str
    name: str
    system_type: str
    description: str | None
    active: bool


class MetadataNamespaceRead(BaseModel):
    id: str
    code: str
    name: str
    namespace_type: str
    physical_name: str | None
    environment: str
    system_code: str
    system_name: str


class MetadataFieldRead(BaseModel):
    id: str
    code: str
    name: str
    data_type: str
    ordinal_position: int
    nullable: bool
    key_field: bool
    classification: str | None
    description: str | None


class MetadataAssetListItem(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    asset_type: str
    layer: str
    physical_name: str | None
    domain_code: str
    domain_name: str
    system_code: str
    system_name: str
    namespace_code: str
    namespace_name: str
    owner_name: str | None
    classification: str
    criticality: str
    status: str
    source_system_code: str | None
    source_asset_code: str | None
    source_contract_version: str | None
    tags: list[str]
    field_count: int
    created_at: datetime
    updated_at: datetime


class MetadataDependencyRead(BaseModel):
    id: str
    dependency_type: str
    upstream_asset_id: str
    upstream_asset_code: str
    upstream_asset_name: str
    downstream_asset_id: str
    downstream_asset_code: str
    downstream_asset_name: str
    description: str | None


class MetadataAssetDetail(MetadataAssetListItem):
    fields: list[MetadataFieldRead]
    upstream_dependencies: list[MetadataDependencyRead]
    downstream_dependencies: list[MetadataDependencyRead]
    attributes: dict[str, object]


class MetadataAssetList(BaseModel):
    total: int
    items: list[MetadataAssetListItem]


class MetadataSummary(BaseModel):
    status: Literal["CONNECTED", "UNAVAILABLE"]
    message: str
    domains: int = 0
    systems: int = 0
    connections: int = 0
    namespaces: int = 0
    assets: int = 0
    fields: int = 0
    dependencies: int = 0
    layers: dict[str, int] = Field(default_factory=dict)


class MetadataSyncResult(BaseModel):
    mode: Literal["LIVE"]
    imported: int
    created: int
    updated: int
    domains: int
    namespaces: int
    message: str
