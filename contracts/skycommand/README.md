# SkyCommand Consumer Boundary

SkyData Studio begins after successful ingestion and consumes the generic contracts established by SkyCommand Phase 16.

Initial accepted inputs:

- `data_catalogue.v1`
- `data_asset.v1`
- `data_metric.v1`
- `data_freshness_status.v1`
- `ingestion_run_summary.v1`
- `ingestion_quality_evidence.v1`
- `time_series_observations.v1`
- `metric_observations.v1`

The Python models in `packages/contracts/skydata_contracts/skycommand.py` intentionally represent the stable consumer fields needed by Studio. They are not copies of SkyCommand database tables.
