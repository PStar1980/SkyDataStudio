from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

type FreshnessStatus = Literal["CURRENT", "WARNING", "ERROR", "INACTIVE", "UNKNOWN"]


class SkyCommandConnection(BaseModel):
    status: Literal["CONNECTED", "PREVIEW", "UNAVAILABLE"]
    message: str
    base_url: str
    authenticated: bool
    contract_versions: list[str] = Field(default_factory=list)


class AssetWorkspaceTotals(BaseModel):
    assets: int = 0
    sources: int = 0
    current: int = 0
    warning: int = 0
    error: int = 0
    inactive: int = 0
    unknown: int = 0
    quality_issues: int = 0


class AssetWorkspaceFilters(BaseModel):
    domains: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    freshness_statuses: list[FreshnessStatus] = Field(default_factory=list)


class AssetWorkspaceItem(BaseModel):
    domain_code: str
    domain_name: str
    asset_code: str
    asset_name: str
    asset_description: str | None = None
    asset_kind_code: str
    frequency_code: str | None = None
    unit_code: str | None = None
    criticality_code: str
    source_code: str | None = None
    source_name: str | None = None
    provider_name: str | None = None
    storage_relation: str | None = None
    freshness_status: FreshnessStatus = "UNKNOWN"
    freshness_reason: str = "UNKNOWN"
    freshness_message: str = "Freshness evidence is unavailable."
    freshness_severity: str = "UNKNOWN"
    source_latest_date: date | None = None
    target_latest_date: date | None = None
    target_row_count: int | None = None
    last_attempt_status: str | None = None
    last_run_status: str | None = None
    quality_issue_count: int = 0
    contract_version: str


class AssetWorkspaceResponse(BaseModel):
    generated_at: datetime
    mode: Literal["LIVE", "PREVIEW"]
    source_system: Literal["SKYCOMMAND"] = "SKYCOMMAND"
    connection: SkyCommandConnection
    totals: AssetWorkspaceTotals
    filters: AssetWorkspaceFilters
    items: list[AssetWorkspaceItem]


class SkyCommandIntegrationHealth(BaseModel):
    checked_at: datetime
    connection: SkyCommandConnection
    domain_count: int = 0
    asset_count: int = 0
