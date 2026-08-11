from datetime import UTC, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from skydata_contracts.skycommand import IngestionRunRecord

from skydata_studio.core.config import Settings, get_settings
from skydata_studio.integrations.airflow import AirflowClient, AirflowClientError
from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.dependencies import (
    SkyCommandGateway,
    SkyCommandGatewayDependency,
)
from skydata_studio.schemas.airflow import (
    AirflowAssetEventSummary,
    AirflowBackfillCreateRequest,
    AirflowBackfillCreateResponse,
    AirflowBackfillList,
    AirflowDagRunDetail,
    AirflowDagRunList,
    AirflowDagRunTriggerRequest,
    AirflowDagRunTriggerResponse,
    AirflowIngestionEventPreview,
    AirflowIngestionEventTriggerRequest,
    AirflowIngestionEventTriggerResponse,
    AirflowIngestionSourceSummary,
    AirflowIntegrationSummary,
)

router = APIRouter()

PROOF_INGESTION_ASSET_URI = "x-skycommand://ingestion/macro/dff"
DEFAULT_INGESTION_DOMAIN = "MACRO"
DEFAULT_INGESTION_SOURCE = "FRED"
DEFAULT_INGESTION_ASSET = "DFF"


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


def _skycommand_unavailable(error: SkyCommandClientError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


def _ingestion_summary(run: IngestionRunRecord) -> AirflowIngestionSourceSummary:
    ingestion_run_id = run.ingestion_run_id
    if ingestion_run_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SkyCommand ingestion evidence does not expose an ingestion run ID.",
        )
    return AirflowIngestionSourceSummary(
        ingestion_run_id=str(ingestion_run_id),
        domain_code=run.domain_code,
        source_code=run.source_code,
        status_code=run.status_code,
        terminal=run.terminal,
        success_like=run.success_like,
        selected_assets=list(run.selected_assets),
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _run_has_asset(
    run: IngestionRunRecord,
    *,
    asset_code: str,
    item_codes: set[str] | None = None,
) -> bool:
    wanted = asset_code.strip().upper()
    selected = {str(item).strip().upper() for item in run.selected_assets}
    return wanted in selected or (item_codes is not None and wanted in item_codes)


async def _resolve_ingestion_source(
    gateway: SkyCommandGateway,
    *,
    ingestion_run_id: str | None,
    domain_code: str,
    source_code: str,
    asset_code: str,
) -> AirflowIngestionSourceSummary | None:
    domain = domain_code.strip().upper()
    source = source_code.strip().upper()
    asset = asset_code.strip().upper()

    async def validate_detail(run_id: str | int) -> AirflowIngestionSourceSummary | None:
        detail = await gateway.get_run(ingestion_run_id=run_id)
        run = detail.run
        item_codes = {item.asset_code.strip().upper() for item in detail.items}
        if (
            run.domain_code.strip().upper() != domain
            or run.source_code.strip().upper() != source
        ):
            return None
        if not run.terminal or not run.success_like:
            return None
        if not _run_has_asset(run, asset_code=asset, item_codes=item_codes):
            return None
        return _ingestion_summary(run)

    if ingestion_run_id:
        return await validate_detail(ingestion_run_id)

    listing = await gateway.list_runs(
        domain_code=domain,
        source_code=source,
        limit=50,
        offset=0,
    )
    for run in listing.items:
        if run.ingestion_run_id is None or not run.terminal or not run.success_like:
            continue
        if _run_has_asset(run, asset_code=asset):
            return _ingestion_summary(run)
        resolved = await validate_detail(run.ingestion_run_id)
        if resolved is not None:
            return resolved
    return None


def _event_for_ingestion_run(
    events: list[AirflowAssetEventSummary],
    ingestion_run_id: str,
) -> AirflowAssetEventSummary | None:
    for event in events:
        if str(event.extra.get("skycommand_ingestion_run_id") or "") == ingestion_run_id:
            return event
    return None


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
    "/dags/{dag_id}/ingestion-events/latest",
    response_model=AirflowIngestionEventPreview,
)
async def airflow_latest_ingestion_event(
    dag_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    gateway: SkyCommandGatewayDependency,
    domain_code: str = DEFAULT_INGESTION_DOMAIN,
    source_code: str = DEFAULT_INGESTION_SOURCE,
    asset_code: str = DEFAULT_INGESTION_ASSET,
) -> AirflowIngestionEventPreview:
    try:
        ingestion_run = await _resolve_ingestion_source(
            gateway,
            ingestion_run_id=None,
            domain_code=domain_code,
            source_code=source_code,
            asset_code=asset_code,
        )
    except SkyCommandClientError as error:
        raise _skycommand_unavailable(error) from error

    airflow = _client(settings)
    try:
        asset = airflow.asset_by_uri(PROOF_INGESTION_ASSET_URI)
        existing_event = None
        if asset is not None and ingestion_run is not None:
            existing_event = _event_for_ingestion_run(
                airflow.asset_events(asset.id, limit=50),
                ingestion_run.ingestion_run_id,
            )
    except AirflowClientError as error:
        raise _service_unavailable(error) from error

    if ingestion_run is None:
        return AirflowIngestionEventPreview(
            dag_id=dag_id,
            asset_uri=PROOF_INGESTION_ASSET_URI,
            asset_registered=asset is not None,
            eligible=False,
            already_emitted=False,
            message=(
                f"No terminal successful {source_code.upper()} ingestion run containing "
                f"{asset_code.upper()} is available yet."
            ),
        )

    if existing_event is not None:
        message = (
            "The latest eligible SkyCommand ingestion run has already emitted "
            "its Airflow asset event."
        )
    elif asset is not None:
        message = (
            "The latest eligible SkyCommand ingestion run is ready to emit "
            "an Airflow asset event."
        )
    else:
        message = (
            "Airflow has not registered the DFF ingestion asset yet; wait for "
            "the DAG processor to reparse the DAG."
        )

    return AirflowIngestionEventPreview(
        dag_id=dag_id,
        asset_uri=PROOF_INGESTION_ASSET_URI,
        asset_registered=asset is not None,
        eligible=asset is not None,
        already_emitted=existing_event is not None,
        ingestion_run=ingestion_run,
        event=existing_event,
        message=message,
    )


@router.post(
    "/dags/{dag_id}/ingestion-events",
    response_model=AirflowIngestionEventTriggerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def airflow_ingestion_event_trigger(
    dag_id: str,
    payload: AirflowIngestionEventTriggerRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    gateway: SkyCommandGatewayDependency,
) -> AirflowIngestionEventTriggerResponse:
    try:
        ingestion_run = await _resolve_ingestion_source(
            gateway,
            ingestion_run_id=payload.ingestion_run_id,
            domain_code=payload.domain_code,
            source_code=payload.source_code,
            asset_code=payload.asset_code,
        )
    except SkyCommandClientError as error:
        raise _skycommand_unavailable(error) from error

    if ingestion_run is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The requested SkyCommand ingestion run is not a terminal successful run "
                f"for {payload.domain_code.upper()}/{payload.source_code.upper()}/"
                f"{payload.asset_code.upper()}."
            ),
        )

    airflow = _client(settings)
    try:
        asset = airflow.asset_by_uri(PROOF_INGESTION_ASSET_URI)
        if asset is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Airflow has not registered the DFF ingestion asset yet. Wait for the DAG "
                    "processor to reparse the Phase 5.4 DAG, then refresh Airflow."
                ),
            )
        events = airflow.asset_events(asset.id, limit=50)
        existing_event = _event_for_ingestion_run(
            events,
            ingestion_run.ingestion_run_id,
        )
        if existing_event is not None:
            return AirflowIngestionEventTriggerResponse(
                dag_id=dag_id,
                asset=asset,
                event=existing_event,
                ingestion_run=ingestion_run,
                reused=True,
            )

        run_date = (
            ingestion_run.completed_at or ingestion_run.started_at
        ).date().isoformat()
        event = airflow.create_asset_event(
            asset.id,
            extra={
                "event_type": "SKYCOMMAND_INGESTION_COMPLETE",
                "contract_version": "ingestion_run_summary.v1",
                "skycommand_ingestion_run_id": ingestion_run.ingestion_run_id,
                "domain_code": payload.domain_code.strip().upper(),
                "source_code": payload.source_code.strip().upper(),
                "asset_code": payload.asset_code.strip().upper(),
                "pipeline_code": payload.pipeline_code.strip().upper(),
                "run_date": run_date,
                "version_number": payload.version_number,
            },
        )
    except AirflowClientError as error:
        raise _service_unavailable(error) from error

    return AirflowIngestionEventTriggerResponse(
        dag_id=dag_id,
        asset=asset,
        event=event,
        ingestion_run=ingestion_run,
        reused=False,
    )


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
