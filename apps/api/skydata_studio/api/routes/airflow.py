from datetime import UTC, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skydata_studio.core.config import Settings, get_settings
from skydata_studio.integrations.airflow import AirflowClient, AirflowClientError
from skydata_studio.schemas.airflow import (
    AirflowBackfillCreateRequest,
    AirflowBackfillCreateResponse,
    AirflowBackfillList,
    AirflowDagRunDetail,
    AirflowDagRunList,
    AirflowDagRunTriggerRequest,
    AirflowDagRunTriggerResponse,
    AirflowIntegrationSummary,
)

router = APIRouter()


def _client(settings: Settings) -> AirflowClient:
    return AirflowClient(
        api_base_url=settings.airflow_api_base_url,
        auth_mode=settings.airflow_api_auth_mode,
        timeout_seconds=settings.airflow_api_timeout_seconds,
        username=settings.airflow_api_username,
        password=settings.airflow_api_password,
        token=settings.airflow_api_token,
    )


def _service_unavailable(error: AirflowClientError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


@router.get("/summary", response_model=AirflowIntegrationSummary)
def airflow_summary(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AirflowIntegrationSummary:
    client = _client(settings)
    try:
        return client.summary()
    except AirflowClientError as error:
        api_base_url = settings.airflow_api_base_url.rstrip("/")
        server_base_url = (
            api_base_url[: -len("/api/v2")]
            if api_base_url.endswith("/api/v2")
            else api_base_url
        )
        return AirflowIntegrationSummary(
            connection_status="UNAVAILABLE",
            api_version="v2",
            api_base_url=api_base_url,
            ui_url=server_base_url,
            auth_mode=settings.airflow_api_auth_mode,
            dag_count=0,
            healthy_components=0,
            component_count=0,
            components=[],
            dags=[],
            error=str(error),
        )


@router.get("/dags/{dag_id}/runs", response_model=AirflowDagRunList)
def airflow_dag_runs(
    dag_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AirflowDagRunList:
    try:
        return _client(settings).dag_runs(dag_id, limit=limit)
    except AirflowClientError as error:
        raise _service_unavailable(error) from error


@router.get(
    "/dags/{dag_id}/runs/{dag_run_id}",
    response_model=AirflowDagRunDetail,
)
def airflow_dag_run_detail(
    dag_id: str,
    dag_run_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AirflowDagRunDetail:
    try:
        return _client(settings).dag_run_detail(dag_id, dag_run_id)
    except AirflowClientError as error:
        raise _service_unavailable(error) from error


@router.post(
    "/dags/{dag_id}/runs",
    response_model=AirflowDagRunTriggerResponse,
    status_code=status.HTTP_201_CREATED,
)
def airflow_dag_run_trigger(
    dag_id: str,
    payload: AirflowDagRunTriggerRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AirflowDagRunTriggerResponse:
    run_date = payload.run_date or datetime.now(UTC).date()
    conf: dict[str, object] = {
        "pipeline_code": payload.pipeline_code.strip().upper(),
        "run_date": run_date.isoformat(),
    }
    if payload.version_number is not None:
        conf["version_number"] = payload.version_number

    try:
        run = _client(settings).trigger_dag_run(dag_id, conf=conf)
    except AirflowClientError as error:
        raise _service_unavailable(error) from error
    return AirflowDagRunTriggerResponse(run=run)


@router.get(
    "/dags/{dag_id}/backfills",
    response_model=AirflowBackfillList,
)
def airflow_backfills(
    dag_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AirflowBackfillList:
    try:
        return _client(settings).backfills(dag_id, limit=limit)
    except AirflowClientError as error:
        raise _service_unavailable(error) from error


@router.post(
    "/dags/{dag_id}/backfills",
    response_model=AirflowBackfillCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def airflow_backfill_create(
    dag_id: str,
    payload: AirflowBackfillCreateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AirflowBackfillCreateResponse:
    conf: dict[str, object] = {
        "pipeline_code": payload.pipeline_code.strip().upper(),
        "trigger_mode": "BACKFILL",
    }
    if payload.version_number is not None:
        conf["version_number"] = payload.version_number

    from_date = datetime.combine(payload.from_date, time.min, tzinfo=UTC)
    to_date = datetime.combine(payload.to_date, time.min, tzinfo=UTC)
    try:
        backfill = _client(settings).create_backfill(
            dag_id,
            from_date=from_date,
            to_date=to_date,
            reprocess_behavior=payload.reprocess_behavior,
            max_active_runs=payload.max_active_runs,
            run_backwards=payload.run_backwards,
            conf=conf,
        )
    except AirflowClientError as error:
        raise _service_unavailable(error) from error
    return AirflowBackfillCreateResponse(backfill=backfill)
