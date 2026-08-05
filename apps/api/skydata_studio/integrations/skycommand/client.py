from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

import httpx
from pydantic import BaseModel, ValidationError
from skydata_contracts.skycommand import (
    AssetFreshnessList,
    AssetFreshnessResponse,
    CatalogueAssetList,
    CatalogueAssetResponse,
    CatalogueDomainList,
    CatalogueSourceList,
    IngestionRunList,
    QualityEventList,
    RejectionEventList,
    RevisionEventList,
)

AuthMode = Literal["internal", "bearer", "none"]
QueryValue = str | int | bool | None
ModelT = TypeVar("ModelT", bound=BaseModel)


class SkyCommandClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        category: str = "REQUEST_FAILED",
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.status_code = status_code


class SkyCommandClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str | None,
        auth_mode: AuthMode = "internal",
        timeout_seconds: float = 8.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token.strip() if token else None
        self.auth_mode = auth_mode
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @property
    def authenticated(self) -> bool:
        return self.auth_mode == "none" or bool(self.token)

    def _headers(self) -> dict[str, str]:
        if self.auth_mode == "none":
            return {"Accept": "application/json"}
        if not self.token:
            raise SkyCommandClientError(
                "SkyCommand API authentication is configured but no token is available.",
                category="CONFIGURATION",
            )
        if self.auth_mode == "bearer":
            return {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.token}",
            }
        return {
            "Accept": "application/json",
            "X-SkyCommand-Internal-Token": self.token,
        }

    @staticmethod
    def _params(values: Mapping[str, QueryValue]) -> dict[str, str]:
        return {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in values.items()
            if value is not None and str(value).strip() != ""
        }

    async def _get(
        self,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
    ) -> dict[str, Any]:
        try:
            headers = self._headers()
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(path, params=self._params(params or {}))
        except SkyCommandClientError:
            raise
        except httpx.RequestError as error:
            raise SkyCommandClientError(
                f"SkyCommand could not be reached: {error}",
                category="CONNECTION",
            ) from error

        if response.status_code >= 400:
            message = f"SkyCommand returned HTTP {response.status_code}."
            try:
                payload = response.json()
                if isinstance(payload, dict) and payload.get("error"):
                    message = str(payload["error"])
            except ValueError:
                pass
            raise SkyCommandClientError(
                message,
                category="HTTP",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as error:
            raise SkyCommandClientError(
                "SkyCommand returned a non-JSON response.",
                category="CONTRACT",
            ) from error

        if not isinstance(payload, dict):
            raise SkyCommandClientError(
                "SkyCommand returned an unexpected response shape.",
                category="CONTRACT",
            )
        if payload.get("ok") is False:
            raise SkyCommandClientError(
                str(payload.get("error") or "SkyCommand request failed."),
                category="REMOTE",
            )
        return cast(dict[str, Any], payload)

    @staticmethod
    def _validate(model_type: type[ModelT], payload: dict[str, Any]) -> ModelT:
        try:
            return model_type.model_validate(payload)
        except ValidationError as error:
            raise SkyCommandClientError(
                f"SkyCommand response failed contract validation: {error}",
                category="CONTRACT",
            ) from error

    async def list_domains(self, *, active: bool = True) -> CatalogueDomainList:
        payload = await self._get("/ingestion/catalogue/domains", params={"active": active})
        return self._validate(CatalogueDomainList, payload)

    async def list_sources(
        self,
        *,
        domain_code: str | None = None,
    ) -> CatalogueSourceList:
        payload = await self._get(
            "/ingestion/catalogue/sources",
            params={
                "domainCode": domain_code,
                "observabilityOnly": True,
                "discoverableOnly": True,
            },
        )
        return self._validate(CatalogueSourceList, payload)

    async def list_assets(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CatalogueAssetList:
        payload = await self._get(
            "/ingestion/catalogue/assets",
            params={
                "domainCode": domain_code,
                "sourceCode": source_code,
                "search": search,
                "active": True,
                "discoverable": True,
                "limit": limit,
                "offset": offset,
            },
        )
        return self._validate(CatalogueAssetList, payload)

    async def list_freshness(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        status_code: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AssetFreshnessList:
        payload = await self._get(
            "/ingestion/catalogue/freshness",
            params={
                "domainCode": domain_code,
                "sourceCode": source_code,
                "statusCode": status_code,
                "search": search,
                "active": True,
                "limit": limit,
                "offset": offset,
            },
        )
        return self._validate(AssetFreshnessList, payload)

    async def list_runs(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> IngestionRunList:
        payload = await self._get(
            "/ingestion/runs",
            params={
                "domainCode": domain_code,
                "sourceCode": source_code,
                "limit": limit,
                "offset": offset,
            },
        )
        return self._validate(IngestionRunList, payload)

    async def get_asset(
        self,
        *,
        domain_code: str,
        asset_code: str,
    ) -> CatalogueAssetResponse:
        payload = await self._get(
            f"/ingestion/catalogue/assets/{domain_code}/{asset_code}"
        )
        return self._validate(CatalogueAssetResponse, payload)

    async def get_freshness(
        self,
        *,
        domain_code: str,
        asset_code: str,
    ) -> AssetFreshnessResponse:
        payload = await self._get(
            f"/ingestion/catalogue/freshness/{domain_code}/{asset_code}"
        )
        return self._validate(AssetFreshnessResponse, payload)

    async def list_quality_events(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        asset_code: str | None = None,
        ingestion_run_id: str | int | None = None,
        check_code: str | None = None,
        severity_code: str | None = None,
        blocking: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> QualityEventList:
        payload = await self._get(
            "/ingestion/quality/events",
            params={
                "domainCode": domain_code,
                "sourceCode": source_code,
                "assetCode": asset_code,
                "ingestionRunId": ingestion_run_id,
                "checkCode": check_code,
                "severityCode": severity_code,
                "blocking": blocking,
                "limit": limit,
                "offset": offset,
            },
        )
        return self._validate(QualityEventList, payload)

    async def list_revision_events(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        asset_code: str | None = None,
        ingestion_run_id: str | int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RevisionEventList:
        payload = await self._get(
            "/ingestion/quality/revisions",
            params={
                "domainCode": domain_code,
                "sourceCode": source_code,
                "assetCode": asset_code,
                "ingestionRunId": ingestion_run_id,
                "limit": limit,
                "offset": offset,
            },
        )
        return self._validate(RevisionEventList, payload)

    async def list_rejection_events(
        self,
        *,
        domain_code: str | None = None,
        source_code: str | None = None,
        asset_code: str | None = None,
        ingestion_run_id: str | int | None = None,
        check_code: str | None = None,
        severity_code: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RejectionEventList:
        payload = await self._get(
            "/ingestion/quality/rejections",
            params={
                "domainCode": domain_code,
                "sourceCode": source_code,
                "assetCode": asset_code,
                "ingestionRunId": ingestion_run_id,
                "checkCode": check_code,
                "severityCode": severity_code,
                "limit": limit,
                "offset": offset,
            },
        )
        return self._validate(RejectionEventList, payload)

