from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, cast

import httpx
from skydata_studio.schemas.airflow import (
    AirflowComponentHealth,
    AirflowDagSummary,
    AirflowIntegrationSummary,
)

QueryValue = str | int | float | bool | None


class AirflowClientError(RuntimeError):
    pass


class AirflowClient:
    def __init__(
        self,
        *,
        api_base_url: str,
        auth_mode: str,
        timeout_seconds: float,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.server_base_url = self._server_base_url(self.api_base_url)
        self.auth_mode = auth_mode
        self.timeout_seconds = timeout_seconds
        self.username = username
        self.password = password
        self.token = token
        self.transport = transport

    @staticmethod
    def _server_base_url(api_base_url: str) -> str:
        suffix = "/api/v2"
        if api_base_url.endswith(suffix):
            return api_base_url[: -len(suffix)]
        return api_base_url

    def _token(self, client: httpx.Client) -> str:
        if self.auth_mode == "bearer":
            if not self.token:
                raise AirflowClientError(
                    "AIRFLOW_API_TOKEN is required when AIRFLOW_API_AUTH_MODE=bearer."
                )
            return self.token

        token_url = f"{self.server_base_url}/auth/token"
        try:
            if self.auth_mode == "simple-all-admins":
                response = client.get(token_url)
            elif self.auth_mode == "simple-credentials":
                if not self.username or not self.password:
                    raise AirflowClientError(
                        "AIRFLOW_API_USERNAME and AIRFLOW_API_PASSWORD are required for "
                        "simple-credentials mode."
                    )
                response = client.post(
                    token_url,
                    json={"username": self.username, "password": self.password},
                )
            else:
                raise AirflowClientError(
                    f"Unsupported Airflow authentication mode: {self.auth_mode}."
                )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise AirflowClientError(
                f"Airflow authentication failed: {error}."
            ) from error

        payload = cast(dict[str, Any], response.json())
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise AirflowClientError(
                "Airflow authentication did not return an access token."
            )
        return access_token

    def _get_json(
        self,
        client: httpx.Client,
        path: str,
        *,
        token: str,
        params: Mapping[str, QueryValue] | None = None,
    ) -> dict[str, Any]:
        try:
            response = client.get(
                f"{self.api_base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise AirflowClientError(
                f"Airflow API request failed for {path}: {error}."
            ) from error
        return cast(dict[str, Any], response.json())

    @staticmethod
    def _component(
        payload: dict[str, Any],
        *,
        code: str,
        label: str,
        heartbeat_field: str | None = None,
    ) -> AirflowComponentHealth:
        raw = payload.get(code)
        if not isinstance(raw, dict):
            return AirflowComponentHealth(code=code, label=label, status="UNKNOWN")
        raw_status = raw.get("status")
        normalized = (
            str(raw_status).strip().upper() if raw_status is not None else "UNKNOWN"
        )
        status: Literal["HEALTHY", "UNHEALTHY", "UNKNOWN"]
        if normalized == "HEALTHY":
            status = "HEALTHY"
        elif normalized == "UNHEALTHY":
            status = "UNHEALTHY"
        else:
            status = "UNKNOWN"
        heartbeat = raw.get(heartbeat_field) if heartbeat_field else None
        return AirflowComponentHealth(
            code=code,
            label=label,
            status=status,
            latest_heartbeat=str(heartbeat) if heartbeat is not None else None,
        )

    @staticmethod
    def _dag(raw: dict[str, Any]) -> AirflowDagSummary:
        raw_tags = raw.get("tags")
        tags: list[str] = []
        if isinstance(raw_tags, list):
            for item in raw_tags:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    tags.append(item["name"])
                elif isinstance(item, str):
                    tags.append(item)

        dag_id = str(raw.get("dag_id") or "")
        display_name = str(raw.get("dag_display_name") or dag_id)
        description = raw.get("description")
        timetable = raw.get("timetable_summary")
        return AirflowDagSummary(
            dag_id=dag_id,
            display_name=display_name,
            description=str(description) if description is not None else None,
            paused=bool(raw.get("is_paused", False)),
            stale=bool(raw.get("is_stale", False)),
            timetable=str(timetable) if timetable is not None else None,
            tags=tags,
        )

    def summary(self) -> AirflowIntegrationSummary:
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                token = self._token(client)
                health_payload = self._get_json(
                    client,
                    "/monitor/health",
                    token=token,
                )
                dag_payload = self._get_json(
                    client,
                    "/dags",
                    token=token,
                    params={"limit": 100, "offset": 0, "exclude_stale": True},
                )
        except AirflowClientError:
            raise
        except Exception as error:
            raise AirflowClientError(f"Airflow integration failed: {error}.") from error

        components = [
            self._component(
                health_payload,
                code="metadatabase",
                label="Metadata Database",
            ),
            self._component(
                health_payload,
                code="scheduler",
                label="Scheduler",
                heartbeat_field="latest_scheduler_heartbeat",
            ),
            self._component(
                health_payload,
                code="dag_processor",
                label="DAG Processor",
                heartbeat_field="latest_dag_processor_heartbeat",
            ),
            self._component(
                health_payload,
                code="triggerer",
                label="Triggerer",
                heartbeat_field="latest_triggerer_heartbeat",
            ),
        ]
        healthy_components = sum(item.status == "HEALTHY" for item in components)
        connection_status: Literal["CONNECTED", "DEGRADED"] = (
            "CONNECTED" if healthy_components == len(components) else "DEGRADED"
        )

        raw_dags = dag_payload.get("dags", [])
        dags = (
            [
                self._dag(item)
                for item in raw_dags
                if isinstance(item, dict) and item.get("dag_id")
            ]
            if isinstance(raw_dags, list)
            else []
        )

        return AirflowIntegrationSummary(
            connection_status=connection_status,
            api_version="v2",
            api_base_url=self.api_base_url,
            ui_url=self.server_base_url,
            auth_mode=self.auth_mode,
            dag_count=int(dag_payload.get("total_entries", len(dags)) or 0),
            healthy_components=healthy_components,
            component_count=len(components),
            components=components,
            dags=dags,
        )
