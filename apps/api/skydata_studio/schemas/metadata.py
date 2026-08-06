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
type MetadataMappingType = Literal[
    "COPY",
    "TRANSFORM",
    "AGGREGATE",
    "JOIN",
    "FILTER",
    "PUBLISH",
]
type MetadataLoadStrategy = Literal[
    "FULL_REPLACE",
    "APPEND",
    "MERGE",
    "INCREMENTAL",
    "SNAPSHOT",
]
type MetadataMappingStatus = Literal["DRAFT", "READY", "ACTIVE", "RETIRED"]
type MetadataTransformationType = Literal[
    "DIRECT",
    "RENAME",
    "CAST",
    "DERIVE",
    "AGGREGATE",
    "CONSTANT",
]


def _normalize_code(value: str) -> str:
    return value.strip().upper().replace(" ", "_")


def _normalize_tags(value: list[str]) -> list[str]:
    return sorted({item.strip().lower() for item in value if item.strip()})


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
        return _normalize_tags(value)


class MetadataAssetGovernanceUpdate(BaseModel):
    description: str | None = None
    owner_name: str | None = Field(default=None, max_length=160)
    owner_email: str | None = Field(default=None, max_length=255)
    classification: MetadataClassification = "INTERNAL"
    criticality: str = Field(default="STANDARD", max_length=40)
    status: str = Field(default="ACTIVE", max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=25)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return _normalize_tags(value)


class MetadataAssetFieldsReplace(BaseModel):
    fields: list[MetadataFieldInput] = Field(default_factory=list, max_length=250)


class MetadataFieldMappingInput(BaseModel):
    source_field_code: str | None = Field(default=None, max_length=128)
    target_field_code: str = Field(min_length=1, max_length=128)
    target_data_type: str = Field(min_length=1, max_length=80)
    transformation_type: MetadataTransformationType = "DIRECT"
    expression: str | None = None
    ordinal_position: int = Field(default=1, ge=1)
    nullable: bool = True
    key_field: bool = False
    description: str | None = None

    @field_validator("source_field_code", "target_field_code")
    @classmethod
    def normalize_optional_code(cls, value: str | None) -> str | None:
        return _normalize_code(value) if value else None


class MetadataMappingCreate(BaseModel):
    code: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=255)
    source_asset_id: str
    target_asset_id: str
    mapping_type: MetadataMappingType = "TRANSFORM"
    load_strategy: MetadataLoadStrategy = "FULL_REPLACE"
    status: MetadataMappingStatus = "DRAFT"
    grain: str | None = Field(default=None, max_length=255)
    business_keys: list[str] = Field(default_factory=list, max_length=25)
    transformation_expression: str | None = None
    description: str | None = None
    field_mappings: list[MetadataFieldMappingInput] = Field(
        default_factory=list,
        max_length=250,
    )

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return _normalize_code(value)

    @field_validator("business_keys")
    @classmethod
    def normalize_business_keys(cls, value: list[str]) -> list[str]:
        return sorted({_normalize_code(item) for item in value if item.strip()})


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
    owner_email: str | None
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


class MetadataMappingAssetRead(BaseModel):
    id: str
    code: str
    name: str
    layer: str
    asset_type: str
    domain_code: str
    system_code: str
    namespace_code: str


class MetadataFieldMappingRead(BaseModel):
    id: str
    source_field_code: str | None
    target_field_code: str
    target_data_type: str
    transformation_type: str
    expression: str | None
    ordinal_position: int
    nullable: bool
    key_field: bool
    description: str | None


class MetadataMappingListItem(BaseModel):
    id: str
    code: str
    name: str
    mapping_type: str
    load_strategy: str
    status: str
    grain: str | None
    business_keys: list[str]
    description: str | None
    source_asset: MetadataMappingAssetRead
    target_asset: MetadataMappingAssetRead
    field_mapping_count: int
    created_at: datetime
    updated_at: datetime


class MetadataMappingDetail(MetadataMappingListItem):
    transformation_expression: str | None
    field_mappings: list[MetadataFieldMappingRead]
    attributes: dict[str, object]


class MetadataAssetDetail(MetadataAssetListItem):
    fields: list[MetadataFieldRead]
    upstream_dependencies: list[MetadataDependencyRead]
    downstream_dependencies: list[MetadataDependencyRead]
    inbound_mappings: list[MetadataMappingListItem]
    outbound_mappings: list[MetadataMappingListItem]
    attributes: dict[str, object]


class MetadataAssetList(BaseModel):
    total: int
    items: list[MetadataAssetListItem]


class MetadataMappingList(BaseModel):
    total: int
    items: list[MetadataMappingListItem]


class MetadataMappingSummary(BaseModel):
    mappings: int = 0
    field_mappings: int = 0
    dependencies: int = 0
    statuses: dict[str, int] = Field(default_factory=dict)
    load_strategies: dict[str, int] = Field(default_factory=dict)


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
    mappings: int = 0
    field_mappings: int = 0
    layers: dict[str, int] = Field(default_factory=dict)


class MetadataSyncResult(BaseModel):
    mode: Literal["LIVE"]
    imported: int
    created: int
    updated: int
    domains: int
    namespaces: int
    message: str
