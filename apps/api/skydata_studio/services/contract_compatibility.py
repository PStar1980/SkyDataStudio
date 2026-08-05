from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Literal

from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.dependencies import SkyCommandGateway
from skydata_studio.integrations.skycommand.preview import (
    preview_assets,
    preview_domains,
    preview_freshness,
    preview_quality_events,
    preview_runs,
)
from skydata_studio.schemas.assets import (
    ContractCompatibilityItem,
    ContractCompatibilityResponse,
    SkyCommandConnection,
)

EXPECTED_CONTRACTS: tuple[str, ...] = (
    "data_catalogue.v1",
    "data_asset.v1",
    "asset_freshness.v1",
    "ingestion_run_summary.v1",
    "ingestion_quality_evidence.v1",
)


def compatibility_items(
    observed_versions: dict[str, str | None],
) -> list[ContractCompatibilityItem]:
    items: list[ContractCompatibilityItem] = []
    for expected_version in EXPECTED_CONTRACTS:
        observed_version = observed_versions.get(expected_version)
        if observed_version is None:
            status: Literal["COMPATIBLE", "MISSING", "INCOMPATIBLE"] = "MISSING"
            message = "No compatible contract response was observed."
        elif observed_version == expected_version:
            status = "COMPATIBLE"
            message = "Observed contract matches the supported version."
        else:
            status = "INCOMPATIBLE"
            message = f"Expected {expected_version}, received {observed_version}."
        items.append(
            ContractCompatibilityItem(
                code=expected_version.removesuffix(".v1"),
                expected_version=expected_version,
                observed_version=observed_version,
                status=status,
                message=message,
            )
        )
    return items


def build_compatibility_response(
    *,
    gateway: SkyCommandGateway,
    mode: Literal["LIVE", "PREVIEW"],
    message: str,
    observed_versions: dict[str, str | None],
) -> ContractCompatibilityResponse:
    items = compatibility_items(observed_versions)
    compatible = sum(item.status == "COMPATIBLE" for item in items)
    incompatible = sum(item.status == "INCOMPATIBLE" for item in items)
    missing = sum(item.status == "MISSING" for item in items)
    versions = sorted(
        version for version in observed_versions.values() if version is not None
    )
    return ContractCompatibilityResponse(
        checked_at=datetime.now(UTC),
        mode=mode,
        status="COMPATIBLE" if compatible == len(items) else "DEGRADED",
        connection=SkyCommandConnection(
            status="CONNECTED" if mode == "LIVE" else "PREVIEW",
            message=message,
            base_url=gateway.base_url,
            authenticated=gateway.authenticated,
            contract_versions=versions,
        ),
        compatible=compatible,
        incompatible=incompatible,
        missing=missing,
        items=items,
    )


def preview_observed_versions() -> dict[str, str | None]:
    assets = preview_assets()
    return {
        "data_catalogue.v1": preview_domains().contract_version,
        "data_asset.v1": assets.items[0].contract_version if assets.items else None,
        "asset_freshness.v1": preview_freshness().contract_version,
        "ingestion_run_summary.v1": preview_runs().contract_version,
        "ingestion_quality_evidence.v1": preview_quality_events().contract_version,
    }


async def check_contract_compatibility(
    gateway: SkyCommandGateway,
    *,
    preview_enabled: bool,
) -> ContractCompatibilityResponse:
    try:
        domains, assets, freshness, runs, quality = await asyncio.gather(
            gateway.list_domains(active=True),
            gateway.list_assets(limit=1),
            gateway.list_freshness(limit=1),
            gateway.list_runs(limit=1),
            gateway.list_quality_events(limit=1),
        )
        observed_versions = {
            "data_catalogue.v1": domains.contract_version,
            "data_asset.v1": (
                assets.items[0].contract_version if assets.items else None
            ),
            "asset_freshness.v1": freshness.contract_version,
            "ingestion_run_summary.v1": runs.contract_version,
            "ingestion_quality_evidence.v1": quality.contract_version,
        }
        return build_compatibility_response(
            gateway=gateway,
            mode="LIVE",
            message="SkyCommand contract compatibility was verified live.",
            observed_versions=observed_versions,
        )
    except SkyCommandClientError as error:
        if not preview_enabled:
            raise
        return build_compatibility_response(
            gateway=gateway,
            mode="PREVIEW",
            message=f"Offline contract diagnostics are active: {error}",
            observed_versions=preview_observed_versions(),
        )
