from skydata_contracts.skycommand import IngestionRunSummary


def test_ingestion_run_summary_accepts_skycommand_camel_case_contract() -> None:
    summary = IngestionRunSummary.model_validate(
        {
            "ingestionRunId": "1001",
            "domainCode": "MACRO",
            "sourceCode": "FRED",
            "modeCode": "INCREMENTAL",
            "triggerCode": "WORKFLOW",
            "outcome": "SUCCESS",
            "startedAt": "2026-08-03T12:00:00Z",
            "completedAt": "2026-08-03T12:00:10Z",
            "durationMs": 10000,
            "totals": {
                "itemsRequested": 1,
                "itemsSucceeded": 1,
                "itemsFailed": 0,
                "rowsStaged": 12,
                "rowsInserted": 2,
                "qualityStatusCode": "PASS",
            },
            "items": [
                {
                    "assetCode": "DFF",
                    "attemptNumber": 1,
                    "outcome": "UPDATED",
                    "rowsInserted": 2,
                    "qualityStatusCode": "PASS",
                }
            ],
        }
    )

    assert summary.source_code == "FRED"
    assert summary.totals.rows_inserted == 2
    assert summary.items[0].asset_code == "DFF"
