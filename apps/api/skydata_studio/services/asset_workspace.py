from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Literal, cast

from skydata_contracts.skycommand import (
    AssetFreshnessList,
    CatalogueAsset,
    CatalogueAssetList,
    CatalogueDomainList,
    CatalogueSourceList,
    IngestionRunList,
    IngestionRunRecord,
)
from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.dependencies import SkyCommandGateway
from skydata_studio.integrations.skycommand.preview import (
    preview_assets,
    preview_domains,
    preview_freshness,
    preview_runs,
    preview_sources,
)
from skydata_studio.schemas.assets import (
    AssetWorkspaceFilters,
    AssetWorkspaceItem,
    AssetWorkspaceResponse,
    AssetWorkspaceTotals,
    FreshnessStatus,
    SkyCommandConnection,
    SkyCommandIntegrationHealth,
)

_FRESHNESS_STATUSES: frozenset[str] = frozenset(
    {"CURRENT", "WARNING", "ERROR", "INACTIVE", "UNKNOWN"}
)


def _canonical_freshness_status(value: str | None) -> FreshnessStatus:
    normalized = (value or "UNKNOWN").upper()
    if normalized in _FRESHNESS_STATUSES:
        return cast(FreshnessStatus, normalized)
    return "UNKNOWN"


def _storage_relation(asset: CatalogueAsset) -> str | None:
    if not asset.storage.relation_name:
        return None
    if asset.storage.schema_name:
        return f"{asset.storage.schema_name}.{asset.storage.relation_name}"
    return asset.storage.relation_name


def _build_response(
    *,
    gateway: SkyCommandGateway,
    mode: Literal["LIVE", "PREVIEW"],
    message: str,
    domains: CatalogueDomainList,
    sources: CatalogueSourceList,
    assets: CatalogueAssetList,
    freshness: AssetFreshnessList,
    runs: IngestionRunList,
) -> AssetWorkspaceResponse:
    freshness_by_asset = {
        (item.domain_code, item.asset_code): item for item in freshness.items
    }
    latest_run_by_source: dict[tuple[str, str], IngestionRunRecord] = {}
    for run in runs.items:
        latest_run_by_source.setdefault((run.domain_code, run.source_code), run)

    workspace_items: list[AssetWorkspaceItem] = []
    for asset in assets.items:
        fresh = freshness_by_asset.get((asset.domain_code, asset.asset_code))
        source_code = asset.source.source_code if asset.source else None
        latest_run = (
            latest_run_by_source.get((asset.domain_code, source_code))
            if source_code
            else None
        )
        workspace_items.append(
            AssetWorkspaceItem(
                domain_code=asset.domain_code,
                domain_name=asset.domain_name,
                asset_code=asset.asset_code,
                asset_name=asset.asset_name,
                asset_description=asset.asset_description,
                asset_kind_code=asset.asset_kind_code,
                frequency_code=asset.frequency_code,
                unit_code=asset.unit_code,
                criticality_code=asset.criticality_code,
                source_code=source_code,
                source_name=asset.source.source_name if asset.source else None,
                provider_name=asset.source.provider_name if asset.source else None,
                storage_relation=_storage_relation(asset),
                freshness_status=_canonical_freshness_status(
                    fresh.freshness.status_code if fresh else None
                ),
                freshness_reason=fresh.freshness.reason_code if fresh else "UNKNOWN",
                freshness_message=(
                    fresh.freshness.message
                    if fresh
                    else "No matching freshness evidence was returned."
                ),
                freshness_severity=(
                    fresh.freshness.severity_code if fresh else "UNKNOWN"
                ),
                source_latest_date=(
                    fresh.evidence.source_latest_date if fresh else None
                ),
                target_latest_date=(
                    fresh.evidence.target_latest_date if fresh else None
                ),
                target_row_count=fresh.evidence.target_row_count if fresh else None,
                last_attempt_status=(
                    fresh.evidence.last_attempt_status if fresh else None
                ),
                last_run_status=latest_run.status_code if latest_run else None,
                quality_issue_count=(
                    latest_run.totals.quality_issue_count if latest_run else 0
                ),
                contract_version=asset.contract_version,
            )
        )

    freshness_counts = {
        "CURRENT": 0,
        "WARNING": 0,
        "ERROR": 0,
        "INACTIVE": 0,
        "UNKNOWN": 0,
    }
    for item in workspace_items:
        freshness_counts[item.freshness_status] += 1

    contract_versions = sorted(
        {
            domains.contract_version,
            sources.contract_version,
            assets.contract_version,
            freshness.contract_version,
            runs.contract_version,
        }
    )
    source_codes = sorted(
        {str(item.source_code) for item in workspace_items if item.source_code}
    )
    domain_codes = sorted({item.domain_code for item in workspace_items})
    status_codes = sorted({item.freshness_status for item in workspace_items})

    return AssetWorkspaceResponse(
        generated_at=datetime.now(UTC),
        mode="LIVE" if mode == "LIVE" else "PREVIEW",
        connection=SkyCommandConnection(
            status="CONNECTED" if mode == "LIVE" else "PREVIEW",
            message=message,
            base_url=gateway.base_url,
            authenticated=gateway.authenticated,
            contract_versions=contract_versions,
        ),
        totals=AssetWorkspaceTotals(
            assets=len(workspace_items),
            sources=len(source_codes),
            current=freshness_counts["CURRENT"],
            warning=freshness_counts["WARNING"],
            error=freshness_counts["ERROR"],
            inactive=freshness_counts["INACTIVE"],
            unknown=freshness_counts["UNKNOWN"],
            quality_issues=sum(
                run.totals.quality_issue_count for run in latest_run_by_source.values()
            ),
        ),
        filters=AssetWorkspaceFilters(
            domains=domain_codes,
            sources=source_codes,
            freshness_statuses=status_codes,
        ),
        items=workspace_items,
    )


def _filter_preview_contracts(
    *,
    domain_code: str | None,
    source_code: str | None,
    freshness_status: str | None,
    search: str | None,
) -> tuple[
    CatalogueDomainList,
    CatalogueSourceList,
    CatalogueAssetList,
    AssetFreshnessList,
    IngestionRunList,
]:
    domains = preview_domains()
    sources = preview_sources()
    assets = preview_assets()
    freshness = preview_freshness()
    runs = preview_runs()

    normalized_domain = domain_code.upper() if domain_code else None
    normalized_source = source_code.upper() if source_code else None
    normalized_status = freshness_status.upper() if freshness_status else None
    normalized_search = search.casefold().strip() if search else None

    def asset_matches(asset: CatalogueAsset) -> bool:
        if normalized_domain and asset.domain_code != normalized_domain:
            return False
        if normalized_source and (
            asset.source is None or asset.source.source_code != normalized_source
        ):
            return False
        if normalized_search:
            search_parts = [
                value
                for value in (
                    asset.asset_code,
                    asset.asset_name,
                    asset.asset_description,
                    asset.source.provider_name if asset.source else None,
                )
                if value
            ]
            haystack = " ".join(search_parts).casefold()
            if normalized_search not in haystack:
                return False
        return True

    assets.items = [item for item in assets.items if asset_matches(item)]
    assets.total = len(assets.items)
    asset_keys = {(item.domain_code, item.asset_code) for item in assets.items}
    freshness.items = [
        item
        for item in freshness.items
        if (item.domain_code, item.asset_code) in asset_keys
        and (not normalized_status or item.freshness.status_code == normalized_status)
    ]
    freshness.total = len(freshness.items)
    freshness_keys = {(item.domain_code, item.asset_code) for item in freshness.items}
    if normalized_status:
        assets.items = [
            item for item in assets.items if (item.domain_code, item.asset_code) in freshness_keys
        ]
        assets.total = len(assets.items)

    sources.items = [
        item
        for item in sources.items
        if (not normalized_domain or item.domain_code == normalized_domain)
        and (not normalized_source or item.source_code == normalized_source)
    ]
    domains.items = [
        item
        for item in domains.items
        if not normalized_domain or item.domain_code == normalized_domain
    ]
    runs.items = [
        item
        for item in runs.items
        if (not normalized_domain or item.domain_code == normalized_domain)
        and (not normalized_source or item.source_code == normalized_source)
    ]
    runs.total = len(runs.items)
    return domains, sources, assets, freshness, runs


async def build_asset_workspace(
    gateway: SkyCommandGateway,
    *,
    domain_code: str | None = None,
    source_code: str | None = None,
    freshness_status: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    preview_enabled: bool = True,
) -> AssetWorkspaceResponse:
    try:
        domains, sources, assets, freshness, runs = await asyncio.gather(
            gateway.list_domains(active=True),
            gateway.list_sources(domain_code=domain_code),
            gateway.list_assets(
                domain_code=domain_code,
                source_code=source_code,
                search=search,
                limit=limit,
                offset=offset,
            ),
            gateway.list_freshness(
                domain_code=domain_code,
                source_code=source_code,
                status_code=freshness_status,
                search=search,
                limit=limit,
                offset=offset,
            ),
            gateway.list_runs(
                domain_code=domain_code,
                source_code=source_code,
                limit=25,
            ),
        )
        return _build_response(
            gateway=gateway,
            mode="LIVE",
            message="Live read-only SkyCommand contracts are connected.",
            domains=domains,
            sources=sources,
            assets=assets,
            freshness=freshness,
            runs=runs,
        )
    except SkyCommandClientError as error:
        if not preview_enabled:
            raise
        domains, sources, assets, freshness, runs = _filter_preview_contracts(
            domain_code=domain_code,
            source_code=source_code,
            freshness_status=freshness_status,
            search=search,
        )
        return _build_response(
            gateway=gateway,
            mode="PREVIEW",
            message=f"Offline preview is active: {error}",
            domains=domains,
            sources=sources,
            assets=assets,
            freshness=freshness,
            runs=runs,
        )


async def check_skycommand_health(
    gateway: SkyCommandGateway,
    *,
    preview_enabled: bool,
) -> SkyCommandIntegrationHealth:
    try:
        domains, assets = await asyncio.gather(
            gateway.list_domains(active=True),
            gateway.list_assets(limit=1),
        )
        return SkyCommandIntegrationHealth(
            checked_at=datetime.now(UTC),
            connection=SkyCommandConnection(
                status="CONNECTED",
                message="Authorized SkyCommand catalogue access succeeded.",
                base_url=gateway.base_url,
                authenticated=gateway.authenticated,
                contract_versions=sorted(
                    {domains.contract_version, assets.contract_version}
                ),
            ),
            domain_count=len(domains.items),
            asset_count=assets.total,
        )
    except SkyCommandClientError as error:
        status: Literal["PREVIEW", "UNAVAILABLE"] = (
            "PREVIEW" if preview_enabled else "UNAVAILABLE"
        )
        return SkyCommandIntegrationHealth(
            checked_at=datetime.now(UTC),
            connection=SkyCommandConnection(
                status=status,
                message=(
                    f"Offline preview is available: {error}"
                    if preview_enabled
                    else f"SkyCommand is unavailable: {error}"
                ),
                base_url=gateway.base_url,
                authenticated=gateway.authenticated,
                contract_versions=[],
            ),
            domain_count=0,
            asset_count=0,
        )
