from datetime import UTC, datetime

from skydata_contracts.skycommand import (
    AssetFreshnessList,
    CatalogueAssetList,
    CatalogueDomainList,
    CatalogueSourceList,
    IngestionRunList,
)

_NOW = datetime.now(UTC).isoformat()


def preview_domains() -> CatalogueDomainList:
    return CatalogueDomainList.model_validate(
        {
            "ok": True,
            "contractVersion": "data_catalogue.v1",
            "generatedAt": _NOW,
            "items": [
                {
                    "domainId": 1,
                    "domainCode": "MACRO",
                    "domainName": "Macroeconomic Indicators",
                    "description": "Portable preview of the SkyCommand macro domain.",
                    "contractVersion": "data_catalogue.v1",
                    "active": True,
                    "counts": {
                        "assets": 6,
                        "activeAssets": 6,
                        "metrics": 0,
                        "activeMetrics": 0,
                        "sources": 3,
                    },
                }
            ],
        }
    )


def preview_sources() -> CatalogueSourceList:
    items = [
        ("FRED", "Federal Reserve Economic Data", "Federal Reserve Bank of St. Louis"),
        ("BOC", "Bank of Canada", "Bank of Canada"),
        ("STATCAN", "Statistics Canada", "Statistics Canada"),
    ]
    return CatalogueSourceList.model_validate(
        {
            "ok": True,
            "contractVersion": "data_catalogue.v1",
            "generatedAt": _NOW,
            "items": [
                {
                    "domainCode": "MACRO",
                    "domainName": "Macroeconomic Indicators",
                    "sourceCode": code,
                    "sourceName": name,
                    "providerName": provider,
                    "providerType": "PUBLIC_API",
                    "observabilityEnabled": True,
                    "discoverable": True,
                }
                for code, name, provider in items
            ],
        }
    )


def preview_assets() -> CatalogueAssetList:
    rows = [
        ("DFF", "Effective Federal Funds Rate", "FRED", "DAILY", "PERCENT", "2026-08-01"),
        ("UNRATE", "US Unemployment Rate", "FRED", "MONTHLY", "PERCENT", "2026-07-01"),
        ("CPIAUCSL", "US Consumer Price Index", "FRED", "MONTHLY", "INDEX", "2026-06-01"),
        ("CA_POLICY_RATE", "Bank of Canada Policy Rate", "BOC", "DAILY", "PERCENT", "2026-07-30"),
        ("CA_CPI", "Canada Consumer Price Index", "STATCAN", "MONTHLY", "INDEX", "2026-06-01"),
        (
            "CA_UNEMPLOYMENT",
            "Canada Unemployment Rate",
            "STATCAN",
            "MONTHLY",
            "PERCENT",
            "2026-07-01",
        ),
    ]
    source_names = {
        "FRED": "Federal Reserve Economic Data",
        "BOC": "Bank of Canada",
        "STATCAN": "Statistics Canada",
    }
    return CatalogueAssetList.model_validate(
        {
            "ok": True,
            "contractVersion": "data_catalogue.v1",
            "generatedAt": _NOW,
            "total": len(rows),
            "limit": 100,
            "offset": 0,
            "items": [
                {
                    "domainCode": "MACRO",
                    "domainName": "Macroeconomic Indicators",
                    "assetCode": code,
                    "assetName": name,
                    "assetDescription": f"Offline preview asset for {name}.",
                    "assetKindCode": "TIME_SERIES",
                    "frequencyCode": frequency,
                    "unitCode": unit,
                    "criticalityCode": "STANDARD",
                    "storage": {
                        "schemaName": "macro",
                        "relationName": code.lower(),
                        "dateColumn": "observation_date",
                        "valueColumn": "value",
                    },
                    "contractVersion": "data_asset.v1",
                    "active": True,
                    "discoverable": True,
                    "source": {
                        "sourceCode": source,
                        "sourceName": source_names[source],
                        "providerName": source_names[source],
                        "providerAssetCode": code,
                        "observabilityEnabled": True,
                        "active": True,
                    },
                    "configuration": {"previewLatestDate": latest_date},
                }
                for code, name, source, frequency, unit, latest_date in rows
            ],
        }
    )



def _preview_source_payload(asset_code: str) -> dict[str, object] | None:
    asset = next(item for item in preview_assets().items if item.asset_code == asset_code)
    if asset.source is None:
        return None
    return asset.source.model_dump(by_alias=True)


def preview_freshness() -> AssetFreshnessList:
    status_rows = [
        ("DFF", "FRESH", "ON_SCHEDULE", "INFO", "2026-08-01", 18750),
        ("UNRATE", "FRESH", "ON_SCHEDULE", "INFO", "2026-07-01", 933),
        ("CPIAUCSL", "WATCH", "SOURCE_RELEASE_PENDING", "WARNING", "2026-06-01", 910),
        ("CA_POLICY_RATE", "FRESH", "ON_SCHEDULE", "INFO", "2026-07-30", 4560),
        ("CA_CPI", "STALE", "TARGET_BEHIND_SOURCE", "ERROR", "2026-06-01", 925),
        ("CA_UNEMPLOYMENT", "WATCH", "SOURCE_RELEASE_PENDING", "WARNING", "2026-07-01", 889),
    ]
    asset_names = {item.asset_code: item.asset_name for item in preview_assets().items}
    return AssetFreshnessList.model_validate(
        {
            "ok": True,
            "contractVersion": "asset_freshness.v1",
            "generatedAt": _NOW,
            "total": len(status_rows),
            "limit": 100,
            "offset": 0,
            "items": [
                {
                    "contractVersion": "asset_freshness.v1",
                    "domainCode": "MACRO",
                    "domainName": "Macroeconomic Indicators",
                    "assetCode": code,
                    "assetName": asset_names[code],
                    "assetKindCode": "TIME_SERIES",
                    "active": True,
                    "discoverable": True,
                    "source": _preview_source_payload(code),
                    "refreshedAt": _NOW,
                    "evidence": {
                        "sourceLatestDate": latest_date,
                        "targetLatestDate": latest_date,
                        "targetRelationExists": True,
                        "targetRowCount": row_count,
                        "lastAttemptAt": _NOW,
                        "lastAttemptStatus": "SUCCESS",
                    },
                    "freshness": {
                        "statusCode": status,
                        "statusName": status.title(),
                        "severityCode": severity,
                        "reasonCode": reason,
                        "reasonName": reason.replace("_", " ").title(),
                        "message": f"Preview freshness classification: {status}.",
                    },
                }
                for code, status, reason, severity, latest_date, row_count in status_rows
            ],
        }
    )


def preview_runs() -> IngestionRunList:
    return IngestionRunList.model_validate(
        {
            "ok": True,
            "contractVersion": "ingestion_run_summary.v1",
            "generatedAt": _NOW,
            "total": 3,
            "limit": 25,
            "offset": 0,
            "items": [
                {
                    "ingestionRunId": "preview-1003",
                    "domainCode": "MACRO",
                    "domainName": "Macroeconomic Indicators",
                    "sourceCode": "STATCAN",
                    "sourceName": "Statistics Canada",
                    "modeCode": "INCREMENTAL",
                    "triggerCode": "WORKFLOW",
                    "statusCode": "SUCCESS",
                    "statusName": "Success",
                    "terminal": True,
                    "successLike": True,
                    "startedAt": _NOW,
                    "completedAt": _NOW,
                    "totals": {"itemsRequested": 2, "itemsSucceeded": 2},
                },
                {
                    "ingestionRunId": "preview-1002",
                    "domainCode": "MACRO",
                    "sourceCode": "BOC",
                    "modeCode": "INCREMENTAL",
                    "triggerCode": "SCHEDULE",
                    "statusCode": "SUCCESS",
                    "terminal": True,
                    "successLike": True,
                    "startedAt": _NOW,
                    "completedAt": _NOW,
                    "totals": {"itemsRequested": 1, "itemsSucceeded": 1},
                },
                {
                    "ingestionRunId": "preview-1001",
                    "domainCode": "MACRO",
                    "sourceCode": "FRED",
                    "modeCode": "INCREMENTAL",
                    "triggerCode": "WORKFLOW",
                    "statusCode": "SUCCESS",
                    "terminal": True,
                    "successLike": True,
                    "startedAt": _NOW,
                    "completedAt": _NOW,
                    "totals": {"itemsRequested": 3, "itemsSucceeded": 3},
                },
            ],
        }
    )
