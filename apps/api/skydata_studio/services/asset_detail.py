from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Literal

from skydata_contracts.skycommand import (
    AssetFreshnessResponse,
    CatalogueAssetResponse,
    IngestionRunList,
    QualityEventList,
    RejectionEventList,
    RevisionEventList,
)
from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.dependencies import SkyCommandGateway
from skydata_studio.integrations.skycommand.preview import (
    preview_asset_detail,
    preview_freshness_detail,
    preview_quality_events,
    preview_rejection_events,
    preview_revision_events,
    preview_runs,
)
from skydata_studio.schemas.assets import (
    AssetDetailResponse,
    AssetEvidenceTotals,
    SkyCommandConnection,
)
from skydata_studio.services.contract_compatibility import (
    build_compatibility_response,
)


def _filter_quality_events(
    events: QualityEventList,
    *,
    domain_code: str,
    asset_code: str,
) -> QualityEventList:
    events.items = [
        item
        for item in events.items
        if item.domain_code == domain_code and item.asset_code == asset_code
    ]
    events.total = len(events.items)
    return events


def _filter_revision_events(
    events: RevisionEventList,
    *,
    domain_code: str,
    asset_code: str,
) -> RevisionEventList:
    events.items = [
        item
        for item in events.items
        if item.domain_code == domain_code and item.asset_code == asset_code
    ]
    events.total = len(events.items)
    return events


def _filter_rejection_events(
    events: RejectionEventList,
    *,
    domain_code: str,
    asset_code: str,
) -> RejectionEventList:
    events.items = [
        item
        for item in events.items
        if item.domain_code == domain_code and item.asset_code == asset_code
    ]
    events.total = len(events.items)
    return events


def _filter_runs(
    runs: IngestionRunList,
    *,
    domain_code: str,
    source_code: str | None,
) -> IngestionRunList:
    runs.items = [
        item
        for item in runs.items
        if item.domain_code == domain_code
        and (source_code is None or item.source_code == source_code)
    ][:5]
    runs.total = len(runs.items)
    return runs


def _build_detail_response(
    *,
    gateway: SkyCommandGateway,
    mode: Literal["LIVE", "PREVIEW"],
    message: str,
    asset_response: CatalogueAssetResponse,
    freshness_response: AssetFreshnessResponse,
    runs: IngestionRunList,
    quality: QualityEventList,
    revisions: RevisionEventList,
    rejections: RejectionEventList,
) -> AssetDetailResponse:
    observed_versions = {
        "data_catalogue.v1": asset_response.contract_version,
        "data_asset.v1": asset_response.asset.contract_version,
        "asset_freshness.v1": freshness_response.contract_version,
        "ingestion_run_summary.v1": runs.contract_version,
        "ingestion_quality_evidence.v1": quality.contract_version,
    }
    compatibility = build_compatibility_response(
        gateway=gateway,
        mode=mode,
        message=message,
        observed_versions=observed_versions,
    )
    connection = SkyCommandConnection(
        status="CONNECTED" if mode == "LIVE" else "PREVIEW",
        message=message,
        base_url=gateway.base_url,
        authenticated=gateway.authenticated,
        contract_versions=compatibility.connection.contract_versions,
    )
    return AssetDetailResponse(
        generated_at=datetime.now(UTC),
        mode=mode,
        connection=connection,
        compatibility=compatibility,
        asset=asset_response.asset,
        freshness=freshness_response.item,
        totals=AssetEvidenceTotals(
            quality_events=quality.total,
            blocking_quality_events=sum(item.blocking for item in quality.items),
            revisions=revisions.total,
            rejections=rejections.total,
            recent_runs=len(runs.items),
        ),
        quality_events=quality.items,
        revisions=revisions.items,
        rejections=rejections.items,
        recent_runs=runs.items,
    )


async def build_asset_detail(
    gateway: SkyCommandGateway,
    *,
    domain_code: str,
    asset_code: str,
    preview_enabled: bool,
) -> AssetDetailResponse:
    normalized_domain = domain_code.upper()
    normalized_asset = asset_code.upper()
    try:
        asset_response, freshness_response = await asyncio.gather(
            gateway.get_asset(
                domain_code=normalized_domain,
                asset_code=normalized_asset,
            ),
            gateway.get_freshness(
                domain_code=normalized_domain,
                asset_code=normalized_asset,
            ),
        )
        source_code = (
            asset_response.asset.source.source_code
            if asset_response.asset.source is not None
            else None
        )
        runs, quality, revisions, rejections = await asyncio.gather(
            gateway.list_runs(
                domain_code=normalized_domain,
                source_code=source_code,
                limit=5,
            ),
            gateway.list_quality_events(
                domain_code=normalized_domain,
                asset_code=normalized_asset,
                limit=25,
            ),
            gateway.list_revision_events(
                domain_code=normalized_domain,
                asset_code=normalized_asset,
                limit=25,
            ),
            gateway.list_rejection_events(
                domain_code=normalized_domain,
                asset_code=normalized_asset,
                limit=25,
            ),
        )
        return _build_detail_response(
            gateway=gateway,
            mode="LIVE",
            message="Live asset and quality evidence are connected.",
            asset_response=asset_response,
            freshness_response=freshness_response,
            runs=runs,
            quality=quality,
            revisions=revisions,
            rejections=rejections,
        )
    except SkyCommandClientError as error:
        if error.status_code == 404 or not preview_enabled:
            raise
        asset_response = preview_asset_detail(normalized_domain, normalized_asset)
        freshness_response = preview_freshness_detail(
            normalized_domain,
            normalized_asset,
        )
        source_code = (
            asset_response.asset.source.source_code
            if asset_response.asset.source is not None
            else None
        )
        runs = _filter_runs(
            preview_runs(),
            domain_code=normalized_domain,
            source_code=source_code,
        )
        quality = _filter_quality_events(
            preview_quality_events(),
            domain_code=normalized_domain,
            asset_code=normalized_asset,
        )
        revisions = _filter_revision_events(
            preview_revision_events(),
            domain_code=normalized_domain,
            asset_code=normalized_asset,
        )
        rejections = _filter_rejection_events(
            preview_rejection_events(),
            domain_code=normalized_domain,
            asset_code=normalized_asset,
        )
        return _build_detail_response(
            gateway=gateway,
            mode="PREVIEW",
            message=f"Offline asset evidence preview is active: {error}",
            asset_response=asset_response,
            freshness_response=freshness_response,
            runs=runs,
            quality=quality,
            revisions=revisions,
            rejections=rejections,
        )
