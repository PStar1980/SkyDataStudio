# SkyCommand Consumer Boundary

SkyData Studio begins after successful ingestion and consumes the generic contracts established by SkyCommand Phase 16.

## Phase 2.1 accepted inputs

- `data_catalogue.v1`
- `data_asset.v1`
- `asset_freshness.v1`
- `ingestion_run_summary.v1`

Initial read-only API routes:

- `GET /api/ingestion/catalogue/domains`
- `GET /api/ingestion/catalogue/sources`
- `GET /api/ingestion/catalogue/assets`
- `GET /api/ingestion/catalogue/freshness`
- `GET /api/ingestion/runs`

SkyData Studio exposes these through its own typed façade under
`/api/v1/integrations/skycommand` and joins catalogue, freshness, and recent-run evidence in the Data Assets workspace.

## Authentication

The preferred local service-to-service mode uses SkyCommand's internal token:

```text
SkyCommand:     SKYCOMMAND_INTERNAL_API_TOKEN=<shared local secret>
SkyData Studio: SKYCOMMAND_API_AUTH_MODE=internal
SkyData Studio: SKYCOMMAND_API_TOKEN=<same shared local secret>
```

SkyCommand grants this identity only the read permissions required by internal services, including `INGESTION_VIEW_STATUS`. Bearer mode remains available for temporary interactive testing with a valid SkyCommand session token.

## Contract rule

The Python models in `packages/contracts/skydata_contracts/skycommand.py` represent stable consumer fields needed by Studio. They are not copies of SkyCommand database tables, and unknown additive fields are tolerated for forward compatibility.

## Freshness vocabulary

SkyData Studio preserves the canonical `asset_freshness.v1` status codes emitted by SkyCommand:

- `CURRENT` — the asset meets its resolved cadence and publication policy;
- `WARNING` — evidence requires attention, but failure is not proven;
- `ERROR` — ingestion, storage, or configuration evidence requires action;
- `INACTIVE` — publication is intentionally inactive or discontinued;
- `UNKNOWN` — available evidence is insufficient for a confident classification.

Preview fixtures, filters, aggregate totals, and row-level UI indicators use this same vocabulary. Unknown legacy or future values are normalized to `UNKNOWN` at the SkyData Studio façade boundary.

## Phase 2.2 quality-evidence boundary

SkyData Studio consumes these additional read-only SkyCommand endpoints:

- `GET /api/ingestion/quality/events`
- `GET /api/ingestion/quality/revisions`
- `GET /api/ingestion/quality/rejections`
- `GET /api/ingestion/catalogue/assets/:domainCode/:assetCode`
- `GET /api/ingestion/catalogue/freshness/:domainCode/:assetCode`

The quality, revision, and rejection collections share
`ingestion_quality_evidence.v1`. SkyData Studio verifies this version alongside
`data_catalogue.v1`, `data_asset.v1`, `asset_freshness.v1`, and
`ingestion_run_summary.v1` before presenting the boundary as compatible.
