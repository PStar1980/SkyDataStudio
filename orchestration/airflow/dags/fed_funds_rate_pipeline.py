"""Airflow-owned batch wrapper for the governed Federal Funds Rate pipeline.

Airflow owns durable orchestration while SkyData Studio retains pipeline execution,
metadata, replay safety, and materialization authority. The DAG talks back to Studio
through its public API and never reads Studio or Airflow metadata databases directly.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from airflow.sdk import (
    Asset,
    AssetOrTimeSchedule,
    CronTriggerTimetable,
    dag,
    get_current_context,
    task,
)

DAG_ID = "skydata_studio_fed_funds_rate_pipeline"
DEFAULT_PIPELINE_CODE = "FED_FUNDS_RATE_PIPELINE"
INGESTION_COMPLETE_ASSET = Asset(
    uri="x-skycommand://ingestion/macro/dff",
    name="skycommand_dff_ingestion_complete",
)
STUDIO_API_BASE_URL = os.environ.get(
    "SKYDATA_STUDIO_API_BASE_URL",
    "http://host.docker.internal:8100/api/v1",
).rstrip("/")


def _request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
    query: dict[str, object] | None = None,
) -> dict[str, Any]:
    url = f"{STUDIO_API_BASE_URL}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - local trusted API
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"SkyData Studio API returned HTTP {error.code}: {detail}"
        ) from error
    except URLError as error:
        raise RuntimeError(
            "SkyData Studio API is unreachable from Airflow. Start the Studio API on "
            "0.0.0.0:8100 for the local Docker callback proof."
        ) from error


@dag(
    dag_id=DAG_ID,
    description="Durably orchestrate the governed Federal Funds Rate Studio pipeline.",
    schedule=AssetOrTimeSchedule(
        timetable=CronTriggerTimetable("0 0 * * *", timezone="UTC"),
        assets=[INGESTION_COMPLETE_ASSET],
    ),
    start_date=datetime(2026, 8, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    tags=[
        "skydata-studio",
        "phase-5",
        "dff",
        "pipeline",
        "scheduled",
        "event-driven",
    ],
)
def fed_funds_rate_pipeline():
    @task(retries=1)
    def resolve_pipeline_contract() -> dict[str, object]:
        context = get_current_context()
        dag_run = context["dag_run"]
        conf = dict(dag_run.conf or {})
        event_extra: dict[str, object] = {}
        triggering_asset_events = context.get("triggering_asset_events")
        if isinstance(triggering_asset_events, dict):
            for raw_events in triggering_asset_events.values():
                if not isinstance(raw_events, list):
                    continue
                for raw_event in reversed(raw_events):
                    raw_extra = (
                        raw_event.get("extra")
                        if isinstance(raw_event, dict)
                        else getattr(raw_event, "extra", None)
                    )
                    if (
                        isinstance(raw_extra, dict)
                        and raw_extra.get("event_type")
                        == "SKYCOMMAND_INGESTION_COMPLETE"
                    ):
                        event_extra = raw_extra
                        break
                if event_extra:
                    break

        pipeline_code = str(
            conf.get("pipeline_code")
            or event_extra.get("pipeline_code")
            or DEFAULT_PIPELINE_CODE
        ).strip().upper()
        configured_run_date = conf.get("run_date") or event_extra.get("run_date")
        if configured_run_date is not None:
            run_date = str(configured_run_date)
        else:
            interval_start = context.get("data_interval_start")
            logical_date = context.get("logical_date")
            schedule_date = interval_start or logical_date
            run_date = (
                schedule_date.date().isoformat()
                if schedule_date is not None
                else datetime.now(UTC).date().isoformat()
            )
        version_number = conf.get("version_number") or event_extra.get("version_number")

        catalogue = _request_json(
            "GET",
            "/pipelines",
            query={"search": pipeline_code, "limit": 20},
        )
        raw_items = catalogue.get("items")
        items = raw_items if isinstance(raw_items, list) else []
        pipeline = next(
            (
                item
                for item in items
                if isinstance(item, dict)
                and str(item.get("code") or "").upper() == pipeline_code
            ),
            None,
        )
        if pipeline is None:
            raise RuntimeError(
                f"SkyData Studio pipeline {pipeline_code} was not found."
            )

        return {
            "pipeline_id": str(pipeline["id"]),
            "pipeline_code": pipeline_code,
            "version_number": version_number,
            "run_date": run_date,
            "airflow_dag_run_id": str(dag_run.run_id),
            "trigger_mode": str(
                event_extra.get("event_type")
                or conf.get("trigger_mode")
                or dag_run.run_type
            ),
            "skycommand_ingestion_run_id": event_extra.get(
                "skycommand_ingestion_run_id"
            ),
            "source_code": event_extra.get("source_code"),
            "asset_code": event_extra.get("asset_code"),
        }

    @task(retries=1, retry_delay=timedelta(seconds=5))
    def execute_studio_pipeline(contract: dict[str, object]) -> dict[str, object]:
        dag_run_id = str(contract["airflow_dag_run_id"])
        payload: dict[str, object] = {
            "pipeline_id": str(contract["pipeline_id"]),
            "parameters": {"RUN_DATE": str(contract["run_date"])},
            "replay_mode": "REUSE",
            "replay_key": f"AIRFLOW:{dag_run_id}",
            "trigger_type": "AIRFLOW",
        }
        if contract.get("version_number") is not None:
            payload["version_number"] = int(str(contract["version_number"]))

        response = _request_json("POST", "/pipeline-runs", payload=payload)
        run = response.get("run")
        if not isinstance(run, dict):
            raise RuntimeError("SkyData Studio did not return pipeline run evidence.")

        return {
            "reused": bool(response.get("reused", False)),
            "studio_run_id": str(run.get("id") or ""),
            "studio_run_key": str(run.get("run_key") or ""),
            "status": str(run.get("status") or "UNKNOWN"),
            "succeeded_steps": int(run.get("succeeded_steps") or 0),
            "failed_steps": int(run.get("failed_steps") or 0),
            "result": run.get("result") if isinstance(run.get("result"), dict) else {},
            "trigger_mode": contract.get("trigger_mode"),
            "skycommand_ingestion_run_id": contract.get(
                "skycommand_ingestion_run_id"
            ),
            "source_code": contract.get("source_code"),
            "asset_code": contract.get("asset_code"),
        }

    @task
    def validate_materialization(execution: dict[str, object]) -> dict[str, object]:
        if execution["status"] != "SUCCEEDED":
            raise RuntimeError(
                f"Studio pipeline finished with status {execution['status']}."
            )
        if int(execution["failed_steps"]) != 0:
            raise RuntimeError("Studio pipeline reported failed steps.")

        result = execution.get("result")
        if not isinstance(result, dict) or not result.get("materialization_executed"):
            raise RuntimeError(
                "Studio pipeline completed without Phase 4.3 materialization execution evidence."
            )
        return execution

    @task
    def publish_batch_evidence(execution: dict[str, object]) -> dict[str, object]:
        result = execution.get("result")
        result_payload = result if isinstance(result, dict) else {}
        return {
            "result_version": "airflow_pipeline_batch.v1",
            "outcome": execution["status"],
            "studio_run_id": execution["studio_run_id"],
            "studio_run_key": execution["studio_run_key"],
            "studio_run_reused": execution["reused"],
            "succeeded_steps": execution["succeeded_steps"],
            "materialization_executed": result_payload.get("materialization_executed"),
            "data_mutation_applied": result_payload.get("data_mutation_applied"),
            "target_relation": result_payload.get("target_relation"),
            "rows_read": result_payload.get("rows_read"),
            "rows_inserted": result_payload.get("rows_inserted"),
            "rows_updated": result_payload.get("rows_updated"),
            "rows_changed": result_payload.get("rows_changed"),
            "rows_unchanged": result_payload.get("rows_unchanged"),
            "rows_rejected": result_payload.get("rows_rejected"),
            "rows_published": result_payload.get("rows_published"),
            "target_row_count": result_payload.get("target_row_count"),
            "trigger_mode": execution.get("trigger_mode"),
            "skycommand_ingestion_run_id": execution.get(
                "skycommand_ingestion_run_id"
            ),
            "source_code": execution.get("source_code"),
            "asset_code": execution.get("asset_code"),
        }

    contract = resolve_pipeline_contract()
    execution = execute_studio_pipeline(contract)
    validated = validate_materialization(execution)
    publish_batch_evidence(validated)


fed_funds_rate_pipeline()
