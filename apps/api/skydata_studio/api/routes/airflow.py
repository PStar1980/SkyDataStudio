from typing import Annotated

from fastapi import APIRouter, Depends

from skydata_studio.core.config import Settings, get_settings
from skydata_studio.integrations.airflow import AirflowClient, AirflowClientError
from skydata_studio.schemas.airflow import AirflowIntegrationSummary

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
