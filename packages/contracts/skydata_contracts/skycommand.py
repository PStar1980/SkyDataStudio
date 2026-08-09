from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SkyCommandContractModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ConsumerContract(BaseModel):
    code: str
    purpose: str
    direction: Literal["SKYCOMMAND_TO_SKYDATA"] = "SKYCOMMAND_TO_SKYDATA"
    access: Literal["READ_ONLY"] = "READ_ONLY"


class CatalogueDomainCounts(SkyCommandContractModel):
    assets: int = 0
    active_assets: int = Field(default=0, alias="activeAssets")
    metrics: int = 0
    active_metrics: int = Field(default=0, alias="activeMetrics")
    sources: int = 0


class CatalogueDomain(SkyCommandContractModel):
    domain_id: int | str | None = Field(default=None, alias="domainId")
    domain_code: str = Field(alias="domainCode")
    domain_name: str = Field(alias="domainName")
    description: str | None = None
    schema_name: str | None = Field(default=None, alias="schemaName")
    contract_version: str = Field(alias="contractVersion")
    active: bool = True
    configuration: dict[str, Any] = Field(default_factory=dict)
    counts: CatalogueDomainCounts = Field(default_factory=CatalogueDomainCounts)


class CatalogueSource(SkyCommandContractModel):
    domain_id: int | str | None = Field(default=None, alias="domainId")
    domain_code: str = Field(alias="domainCode")
    domain_name: str = Field(alias="domainName")
    source_id: int | str | None = Field(default=None, alias="sourceId")
    source_code: str = Field(alias="sourceCode")
    source_name: str = Field(alias="sourceName")
    provider_name: str | None = Field(default=None, alias="providerName")
    provider_type: str | None = Field(default=None, alias="providerType")
    description: str | None = None
    observability_enabled: bool = Field(default=False, alias="observabilityEnabled")
    discoverable: bool = True
    aliases: list[str] = Field(default_factory=list)
    tool_codes: list[str] = Field(default_factory=list, alias="toolCodes")
    adapter_codes: list[str] = Field(default_factory=list, alias="adapterCodes")
    source_configuration: dict[str, Any] = Field(
        default_factory=dict, alias="sourceConfiguration"
    )


class CatalogueAssetSource(SkyCommandContractModel):
    source_id: int | str | None = Field(default=None, alias="sourceId")
    source_code: str = Field(alias="sourceCode")
    source_name: str = Field(alias="sourceName")
    provider_name: str | None = Field(default=None, alias="providerName")
    provider_type: str | None = Field(default=None, alias="providerType")
    observability_enabled: bool = Field(default=False, alias="observabilityEnabled")
    provider_asset_code: str | None = Field(default=None, alias="providerAssetCode")
    provider_resource_code: str | None = Field(default=None, alias="providerResourceCode")
    provider_locator: str | None = Field(default=None, alias="providerLocator")
    source_frequency_code: str | None = Field(default=None, alias="sourceFrequencyCode")
    transform_code: str | None = Field(default=None, alias="transformCode")
    configuration: dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class CatalogueAssetStorage(SkyCommandContractModel):
    schema_name: str | None = Field(default=None, alias="schemaName")
    relation_name: str | None = Field(default=None, alias="relationName")
    date_column: str | None = Field(default=None, alias="dateColumn")
    value_column: str | None = Field(default=None, alias="valueColumn")


class CatalogueAsset(SkyCommandContractModel):
    domain_id: int | str | None = Field(default=None, alias="domainId")
    domain_code: str = Field(alias="domainCode")
    domain_name: str = Field(alias="domainName")
    asset_id: int | str | None = Field(default=None, alias="assetId")
    asset_code: str = Field(alias="assetCode")
    asset_name: str = Field(alias="assetName")
    asset_description: str | None = Field(default=None, alias="assetDescription")
    asset_kind_code: str = Field(alias="assetKindCode")
    frequency_code: str | None = Field(default=None, alias="frequencyCode")
    unit_code: str | None = Field(default=None, alias="unitCode")
    scale_code: str | None = Field(default=None, alias="scaleCode")
    geography_code: str | None = Field(default=None, alias="geographyCode")
    seasonal_adjustment_code: str | None = Field(
        default=None, alias="seasonalAdjustmentCode"
    )
    transform_code: str | None = Field(default=None, alias="transformCode")
    release_lag_days: int | None = Field(default=None, alias="releaseLagDays")
    freshness_tolerance_days: int | None = Field(
        default=None, alias="freshnessToleranceDays"
    )
    revisions_expected: bool | None = Field(default=None, alias="revisionsExpected")
    criticality_code: str = Field(default="STANDARD", alias="criticalityCode")
    storage: CatalogueAssetStorage = Field(default_factory=CatalogueAssetStorage)
    contract_version: str = Field(alias="contractVersion")
    configuration: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    source: CatalogueAssetSource | None = None
    discoverable: bool = True


class TimeSeriesObservationAsset(SkyCommandContractModel):
    domain_code: str = Field(alias="domainCode")
    domain_name: str | None = Field(default=None, alias="domainName")
    asset_code: str = Field(alias="assetCode")
    asset_name: str = Field(alias="assetName")
    asset_kind_code: str = Field(alias="assetKindCode")
    frequency_code: str | None = Field(default=None, alias="frequencyCode")
    unit_code: str | None = Field(default=None, alias="unitCode")
    scale_code: str | None = Field(default=None, alias="scaleCode")
    geography_code: str | None = Field(default=None, alias="geographyCode")
    source: CatalogueAssetSource | None = None
    contract_version: str = Field(alias="contractVersion")


class TimeSeriesObservation(SkyCommandContractModel):
    observation_date: date = Field(alias="observationDate")
    value: int | float | str


class TimeSeriesObservationList(SkyCommandContractModel):
    ok: bool = True
    generated_at: datetime = Field(alias="generatedAt")
    contract_version: str = Field(alias="contractVersion")
    asset: TimeSeriesObservationAsset
    total: int = 0
    limit: int = 250
    offset: int = 0
    sort_direction: Literal["ASC", "DESC"] = Field(default="ASC", alias="sortDirection")
    date_from: date | None = Field(default=None, alias="dateFrom")
    date_to: date | None = Field(default=None, alias="dateTo")
    operator: str = "IDENTITY"
    items: list[TimeSeriesObservation] = Field(default_factory=list)


class FreshnessSource(SkyCommandContractModel):
    source_id: int | str | None = Field(default=None, alias="sourceId")
    source_code: str = Field(alias="sourceCode")
    source_name: str = Field(alias="sourceName")
    provider_name: str | None = Field(default=None, alias="providerName")
    provider_asset_code: str | None = Field(default=None, alias="providerAssetCode")


class FreshnessPolicy(SkyCommandContractModel):
    frequency_code: str | None = Field(default=None, alias="frequencyCode")
    origin_code: str | None = Field(default=None, alias="originCode")
    release_lag_days: int | None = Field(default=None, alias="releaseLagDays")
    freshness_tolerance_days: int | None = Field(
        default=None, alias="freshnessToleranceDays"
    )
    expected_latest_date: date | None = Field(default=None, alias="expectedLatestDate")


class FreshnessEvidence(SkyCommandContractModel):
    source_latest_date: date | None = Field(default=None, alias="sourceLatestDate")
    target_relation_exists: bool | None = Field(default=None, alias="targetRelationExists")
    target_row_count: int | None = Field(default=None, alias="targetRowCount")
    target_min_date: date | None = Field(default=None, alias="targetMinDate")
    target_latest_date: date | None = Field(default=None, alias="targetLatestDate")
    source_target_gap_days: int | None = Field(default=None, alias="sourceTargetGapDays")
    last_attempt_at: datetime | None = Field(default=None, alias="lastAttemptAt")
    last_attempt_status: str | None = Field(default=None, alias="lastAttemptStatus")
    last_success_at: datetime | None = Field(default=None, alias="lastSuccessAt")
    details: dict[str, Any] = Field(default_factory=dict)


class FreshnessAssessment(SkyCommandContractModel):
    status_code: str = Field(default="UNKNOWN", alias="statusCode")
    status_name: str = Field(default="Unknown", alias="statusName")
    severity_code: str = Field(default="UNKNOWN", alias="severityCode")
    reason_code: str = Field(default="UNKNOWN", alias="reasonCode")
    reason_name: str = Field(default="Unknown", alias="reasonName")
    message: str = "Freshness evidence is unavailable."


class AssetFreshness(SkyCommandContractModel):
    contract_version: str = Field(alias="contractVersion")
    domain_code: str = Field(alias="domainCode")
    domain_name: str = Field(alias="domainName")
    asset_id: int | str | None = Field(default=None, alias="assetId")
    asset_code: str = Field(alias="assetCode")
    asset_name: str = Field(alias="assetName")
    asset_kind_code: str = Field(alias="assetKindCode")
    frequency_code: str | None = Field(default=None, alias="frequencyCode")
    active: bool = True
    discoverable: bool = True
    source: FreshnessSource | None = None
    refreshed_at: datetime | None = Field(default=None, alias="refreshedAt")
    policy: FreshnessPolicy = Field(default_factory=FreshnessPolicy)
    evidence: FreshnessEvidence = Field(default_factory=FreshnessEvidence)
    freshness: FreshnessAssessment = Field(default_factory=FreshnessAssessment)


class IngestionRunTotals(SkyCommandContractModel):
    items_requested: int = Field(default=0, alias="itemsRequested")
    items_succeeded: int = Field(default=0, alias="itemsSucceeded")
    items_failed: int = Field(default=0, alias="itemsFailed")
    items_updated: int = Field(default=0, alias="itemsUpdated")
    items_unchanged: int = Field(default=0, alias="itemsUnchanged")
    rows_staged: int = Field(default=0, alias="rowsStaged")
    rows_detected_as_new: int = Field(default=0, alias="rowsDetectedAsNew")
    rows_inserted: int = Field(default=0, alias="rowsInserted")
    rows_updated: int = Field(default=0, alias="rowsUpdated")
    rows_unchanged: int = Field(default=0, alias="rowsUnchanged")
    rows_rejected: int = Field(default=0, alias="rowsRejected")
    revisions_detected: int = Field(default=0, alias="revisionsDetected")
    quality_issue_count: int = Field(default=0, alias="qualityIssueCount")
    quality_status_code: str = Field(default="PASS", alias="qualityStatusCode")
    attempts: int = 0
    retries: int = 0


class IngestionRunError(SkyCommandContractModel):
    category_code: str | None = Field(default=None, alias="categoryCode")
    code: str | None = None
    message: str | None = None


class IngestionRunRecord(SkyCommandContractModel):
    ingestion_run_id: int | str | None = Field(default=None, alias="ingestionRunId")
    domain_code: str = Field(alias="domainCode")
    domain_name: str | None = Field(default=None, alias="domainName")
    source_code: str = Field(alias="sourceCode")
    source_name: str | None = Field(default=None, alias="sourceName")
    tool_code: str | None = Field(default=None, alias="toolCode")
    tool_label: str | None = Field(default=None, alias="toolLabel")
    mode_code: str = Field(alias="modeCode")
    trigger_code: str = Field(alias="triggerCode")
    status_code: str = Field(alias="statusCode")
    status_name: str | None = Field(default=None, alias="statusName")
    terminal: bool = False
    success_like: bool = Field(default=False, alias="successLike")
    contract_version: str = Field(default="ingestion_run_summary.v1", alias="contractVersion")
    selected_assets: list[str] = Field(default_factory=list, alias="selectedAssets")
    totals: IngestionRunTotals = Field(default_factory=IngestionRunTotals)
    error: IngestionRunError | None = None
    summary: str | None = None
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    duration_ms: int | None = Field(default=None, alias="durationMs")
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionRunItem(SkyCommandContractModel):
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


class IngestionRunSummary(SkyCommandContractModel):
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


class CatalogueDomainList(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    items: list[CatalogueDomain] = Field(default_factory=list)


class CatalogueSourceList(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    items: list[CatalogueSource] = Field(default_factory=list)


class CatalogueAssetList(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    total: int = 0
    limit: int = 100
    offset: int = 0
    items: list[CatalogueAsset] = Field(default_factory=list)


class AssetFreshnessList(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    total: int = 0
    limit: int = 100
    offset: int = 0
    items: list[AssetFreshness] = Field(default_factory=list)


class IngestionRunList(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    total: int = 0
    limit: int = 50
    offset: int = 0
    items: list[IngestionRunRecord] = Field(default_factory=list)


class CatalogueAssetResponse(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    asset: CatalogueAsset


class AssetFreshnessResponse(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    item: AssetFreshness


class QualityEvent(SkyCommandContractModel):
    event_type: Literal["QUALITY"] = Field(default="QUALITY", alias="eventType")
    quality_event_id: int | str | None = Field(default=None, alias="qualityEventId")
    ingestion_run_id: int | str | None = Field(default=None, alias="ingestionRunId")
    ingestion_run_item_id: int | str | None = Field(
        default=None,
        alias="ingestionRunItemId",
    )
    domain_code: str = Field(alias="domainCode")
    source_code: str = Field(alias="sourceCode")
    asset_code: str = Field(alias="assetCode")
    asset_name: str | None = Field(default=None, alias="assetName")
    check_code: str = Field(alias="checkCode")
    check_name: str | None = Field(default=None, alias="checkName")
    severity_code: str = Field(alias="severityCode")
    blocking: bool = False
    observation_key: str | None = Field(default=None, alias="observationKey")
    source_row_number: int | None = Field(default=None, alias="sourceRowNumber")
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(alias="createdAt")


class RevisionEvent(SkyCommandContractModel):
    event_type: Literal["REVISION"] = Field(default="REVISION", alias="eventType")
    revision_event_id: int | str | None = Field(default=None, alias="revisionEventId")
    ingestion_run_id: int | str | None = Field(default=None, alias="ingestionRunId")
    ingestion_run_item_id: int | str | None = Field(
        default=None,
        alias="ingestionRunItemId",
    )
    domain_code: str = Field(alias="domainCode")
    source_code: str = Field(alias="sourceCode")
    asset_code: str = Field(alias="assetCode")
    asset_name: str | None = Field(default=None, alias="assetName")
    observation_key: str = Field(alias="observationKey")
    observation_date: date | None = Field(default=None, alias="observationDate")
    old_value: Any = Field(default=None, alias="oldValue")
    new_value: Any = Field(default=None, alias="newValue")
    detected_at: datetime = Field(alias="detectedAt")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(alias="createdAt")


class RejectionEvent(SkyCommandContractModel):
    event_type: Literal["REJECTION"] = Field(default="REJECTION", alias="eventType")
    rejection_event_id: int | str | None = Field(default=None, alias="rejectionEventId")
    ingestion_run_id: int | str | None = Field(default=None, alias="ingestionRunId")
    ingestion_run_item_id: int | str | None = Field(
        default=None,
        alias="ingestionRunItemId",
    )
    domain_code: str = Field(alias="domainCode")
    source_code: str = Field(alias="sourceCode")
    asset_code: str = Field(alias="assetCode")
    asset_name: str | None = Field(default=None, alias="assetName")
    check_code: str = Field(alias="checkCode")
    check_name: str | None = Field(default=None, alias="checkName")
    severity_code: str = Field(alias="severityCode")
    source_row_number: int | None = Field(default=None, alias="sourceRowNumber")
    observation_key: str | None = Field(default=None, alias="observationKey")
    raw_payload: dict[str, Any] = Field(default_factory=dict, alias="rawPayload")
    normalized_payload: dict[str, Any] = Field(
        default_factory=dict,
        alias="normalizedPayload",
    )
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(alias="createdAt")


class QualityEventList(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    total: int = 0
    limit: int = 50
    offset: int = 0
    items: list[QualityEvent] = Field(default_factory=list)


class RevisionEventList(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    total: int = 0
    limit: int = 50
    offset: int = 0
    items: list[RevisionEvent] = Field(default_factory=list)


class RejectionEventList(SkyCommandContractModel):
    ok: bool = True
    contract_version: str = Field(alias="contractVersion")
    generated_at: datetime = Field(alias="generatedAt")
    total: int = 0
    limit: int = 50
    offset: int = 0
    items: list[RejectionEvent] = Field(default_factory=list)
