from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal, cast
from urllib.parse import quote
from uuid import uuid4

import httpx
from skydata_studio.schemas.airflow import (
    AirflowBackfillList,
    AirflowBackfillSummary,
    AirflowComponentHealth,
    AirflowDagRunDetail,
    AirflowDagRunList,
    AirflowDagRunSummary,
    AirflowDagSummary,
    AirflowIntegrationSummary,
    AirflowTaskInstanceSummary,
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

    def _post_json(
        self,
        client: httpx.Client,
        path: str,
        *,
        token: str,
        payload: Mapping[str, object],
    ) -> dict[str, Any]:
        try:
            response = client.post(
                f"{self.api_base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                json=dict(payload),
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

    @staticmethod
    def _required_datetime(raw: object, *, field_name: str) -> datetime:
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, str):
            normalized = raw.strip()
            if normalized.endswith("Z"):
                normalized = f"{normalized[:-1]}+00:00"
            try:
                return datetime.fromisoformat(normalized)
            except ValueError as error:
                raise AirflowClientError(
                    f"Airflow response field '{field_name}' is not a valid ISO datetime."
                ) from error
        raise AirflowClientError(
            f"Airflow response field '{field_name}' is missing or invalid."
        )

    @staticmethod
    def _backfill(raw: dict[str, Any]) -> AirflowBackfillSummary:
        return AirflowBackfillSummary(
            id=int(raw.get("id") or 0),
            dag_id=str(raw.get("dag_id") or ""),
            from_date=AirflowClient._required_datetime(
                raw.get("from_date"),
                field_name="from_date",
            ),
            to_date=AirflowClient._required_datetime(
                raw.get("to_date"),
                field_name="to_date",
            ),
            is_paused=bool(raw.get("is_paused", False)),
            reprocess_behavior=str(raw.get("reprocess_behavior") or "none"),
            max_active_runs=int(raw.get("max_active_runs") or 1),
            run_backwards=bool(raw.get("run_backwards", False)),
            created_at=raw.get("created_at"),
            completed_at=raw.get("completed_at"),
            updated_at=raw.get("updated_at"),
        )

    @staticmethod
    def _dag_run(raw: dict[str, Any]) -> AirflowDagRunSummary:
        raw_conf = raw.get("conf")
        return AirflowDagRunSummary(
            dag_id=str(raw.get("dag_id") or ""),
            dag_run_id=str(raw.get("dag_run_id") or ""),
            state=str(raw.get("state") or "UNKNOWN").upper(),
            run_type=str(raw["run_type"]) if raw.get("run_type") is not None else None,
            logical_date=raw.get("logical_date"),
            queued_at=raw.get("queued_at"),
            start_date=raw.get("start_date"),
            end_date=raw.get("end_date"),
            conf=cast(dict[str, object], raw_conf) if isinstance(raw_conf, dict) else {},
        )

    @staticmethod
    def _task_instance(raw: dict[str, Any]) -> AirflowTaskInstanceSummary:
        task_id = str(raw.get("task_id") or "")
        raw_map_index = raw.get("map_index")
        map_index = raw_map_index if isinstance(raw_map_index, int) else -1
        return AirflowTaskInstanceSummary(
            task_id=task_id,
            task_display_name=str(raw.get("task_display_name") or task_id),
            state=str(raw.get("state") or "UNKNOWN").upper(),
            try_number=int(raw.get("try_number") or 0),
            map_index=map_index,
            start_date=raw.get("start_date"),
            end_date=raw.get("end_date"),
            duration=float(raw["duration"]) if raw.get("duration") is not None else None,
            operator=str(raw["operator"]) if raw.get("operator") is not None else None,
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

    def dag_runs(self, dag_id: str, *, limit: int = 20) -> AirflowDagRunList:
        path = f"/dags/{quote(dag_id, safe='')}/dagRuns"
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                token = self._token(client)
                payload = self._get_json(
                    client,
                    path,
                    token=token,
                    params={"limit": limit, "offset": 0},
                )
        except AirflowClientError:
            raise
        except Exception as error:
            raise AirflowClientError(f"Airflow integration failed: {error}.") from error

        raw_runs = payload.get("dag_runs", [])
        items = (
            [self._dag_run(item) for item in raw_runs if isinstance(item, dict)]
            if isinstance(raw_runs, list)
            else []
        )
        fallback_date = datetime.min.replace(tzinfo=UTC)
        items.sort(
            key=lambda item: item.start_date
            or item.queued_at
            or item.logical_date
            or fallback_date,
            reverse=True,
        )
        return AirflowDagRunList(
            dag_id=dag_id,
            total=int(payload.get("total_entries", len(items)) or 0),
            items=items,
        )

    def trigger_dag_run(
        self,
        dag_id: str,
        *,
        conf: Mapping[str, object],
    ) -> AirflowDagRunSummary:
        path = f"/dags/{quote(dag_id, safe='')}/dagRuns"
        dag_run_id = f"skydata__{uuid4().hex}"
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                token = self._token(client)
                payload = self._post_json(
                    client,
                    path,
                    token=token,
                    payload={
                        "dag_run_id": dag_run_id,
                        "logical_date": None,
                        "conf": dict(conf),
                    },
                )
        except AirflowClientError:
            raise
        except Exception as error:
            raise AirflowClientError(f"Airflow integration failed: {error}.") from error
        return self._dag_run(payload)

    def dag_run_detail(self, dag_id: str, dag_run_id: str) -> AirflowDagRunDetail:
        encoded_dag_id = quote(dag_id, safe="")
        encoded_run_id = quote(dag_run_id, safe="")
        run_path = f"/dags/{encoded_dag_id}/dagRuns/{encoded_run_id}"
        task_path = f"{run_path}/taskInstances"
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                token = self._token(client)
                run_payload = self._get_json(client, run_path, token=token)
                task_payload = self._get_json(
                    client,
                    task_path,
                    token=token,
                    params={"limit": 100, "offset": 0},
                )
        except AirflowClientError:
            raise
        except Exception as error:
            raise AirflowClientError(f"Airflow integration failed: {error}.") from error

        raw_tasks = task_payload.get("task_instances", [])
        tasks = (
            [self._task_instance(item) for item in raw_tasks if isinstance(item, dict)]
            if isinstance(raw_tasks, list)
            else []
        )
        tasks.sort(key=lambda item: (item.task_id, item.map_index))
        counts = Counter(item.state for item in tasks)
        return AirflowDagRunDetail(
            run=self._dag_run(run_payload),
            tasks=tasks,
            task_state_counts=dict(sorted(counts.items())),
            studio_run_key=f"AIRFLOW:{dag_run_id}",
        )

    def backfills(self, dag_id: str, *, limit: int = 20) -> AirflowBackfillList:
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                token = self._token(client)
                payload = self._get_json(
                    client,
                    "/backfills",
                    token=token,
                    params={"dag_id": dag_id, "limit": limit, "offset": 0},
                )
        except AirflowClientError:
            raise
        except Exception as error:
            raise AirflowClientError(f"Airflow integration failed: {error}.") from error

        raw_backfills = payload.get("backfills", [])
        items = (
            [self._backfill(item) for item in raw_backfills if isinstance(item, dict)]
            if isinstance(raw_backfills, list)
            else []
        )
        items.sort(
            key=lambda item: item.created_at or item.from_date,
            reverse=True,
        )
        return AirflowBackfillList(
            dag_id=dag_id,
            total=int(payload.get("total_entries", len(items)) or len(items)),
            items=items,
        )

    def create_backfill(
        self,
        dag_id: str,
        *,
        from_date: datetime,
        to_date: datetime,
        reprocess_behavior: str,
        max_active_runs: int,
        run_backwards: bool,
        conf: Mapping[str, object],
    ) -> AirflowBackfillSummary:
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                token = self._token(client)
                payload = self._post_json(
                    client,
                    "/backfills",
                    token=token,
                    payload={
                        "dag_id": dag_id,
                        "from_date": from_date.isoformat(),
                        "to_date": to_date.isoformat(),
                        "run_backwards": run_backwards,
                        "dag_run_conf": dict(conf),
                        "reprocess_behavior": reprocess_behavior,
                        "max_active_runs": max_active_runs,
                    },
                )
        except AirflowClientError:
            raise
        except Exception as error:
            raise AirflowClientError(f"Airflow integration failed: {error}.") from error
        return self._backfill(payload)
