from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from skydata_studio.db.base import Base
from skydata_studio.db.session import get_session
from skydata_studio.integrations.skycommand.dependencies import get_skycommand_gateway
from skydata_studio.main import app
from skydata_studio.schemas.metadata import MetadataAssetCreate
from skydata_studio.services.metadata_registry import (
    get_metadata_asset,
    list_metadata_assets,
    metadata_summary,
    register_metadata_asset,
    synchronize_skycommand_assets,
)

from tests.test_asset_workspace import PreviewGateway

pytestmark = pytest.mark.anyio


@pytest.fixture
def registry_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _operations_asset() -> MetadataAssetCreate:
    return MetadataAssetCreate.model_validate(
        {
            "domain": {"code": "OPERATIONS", "name": "Operations"},
            "system": {"code": "CRM", "name": "Customer Relationship Management"},
            "namespace": {"code": "PUBLIC", "name": "Public"},
            "code": "CUSTOMER_ACCOUNT",
            "name": "Customer Account",
            "asset_type": "TABLE",
            "layer": "RAW",
            "physical_name": "customer_account",
            "owner_name": "Operations Analytics",
            "classification": "CONFIDENTIAL",
            "tags": ["Customer", "Operations"],
            "fields": [
                {
                    "code": "CUSTOMER_ID",
                    "data_type": "BIGINT",
                    "ordinal_position": 1,
                    "nullable": False,
                    "key_field": True,
                },
                {
                    "code": "ACCOUNT_STATUS",
                    "data_type": "VARCHAR(30)",
                    "ordinal_position": 2,
                },
            ],
        }
    )


def test_registry_persists_non_macro_product(registry_session: Session) -> None:
    created = register_metadata_asset(registry_session, _operations_asset())

    assert created.code == "CUSTOMER_ACCOUNT"
    assert created.domain_code == "OPERATIONS"
    assert created.system_code == "CRM"
    assert created.classification == "CONFIDENTIAL"
    assert created.tags == ["customer", "operations"]
    assert len(created.fields) == 2
    assert created.fields[0].key_field is True

    summary = metadata_summary(registry_session)
    assert summary.assets == 1
    assert summary.fields == 2
    assert summary.layers == {"RAW": 1}

    listed = list_metadata_assets(registry_session, domain_code="OPERATIONS")
    assert listed.total == 1
    assert listed.items[0].field_count == 2
    assert get_metadata_asset(registry_session, created.id).name == "Customer Account"


async def test_registry_synchronizes_skycommand_assets(registry_session: Session) -> None:
    first = await synchronize_skycommand_assets(registry_session, PreviewGateway())
    second = await synchronize_skycommand_assets(registry_session, PreviewGateway())

    assert first.imported == 6
    assert first.created == 6
    assert first.updated == 0
    assert second.created == 0
    assert second.updated == 6

    summary = metadata_summary(registry_session)
    assert summary.assets == 6
    assert summary.domains == 1
    assert summary.systems == 1
    assert summary.connections == 1
    assert summary.layers == {"RAW": 6}

    dff = list_metadata_assets(registry_session, search="DFF")
    assert dff.total == 1
    assert dff.items[0].source_system_code == "FRED"
    assert dff.items[0].source_contract_version == "data_asset.v1"


async def test_metadata_registry_api(registry_session: Session) -> None:
    def override_session() -> Generator[Session, None, None]:
        yield registry_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_skycommand_gateway] = PreviewGateway
    client = TestClient(app)
    try:
        create_response = client.post(
            "/api/v1/metadata/assets",
            json=_operations_asset().model_dump(mode="json"),
        )
        assert create_response.status_code == 201
        assert create_response.json()["domain_code"] == "OPERATIONS"

        sync_response = client.post("/api/v1/metadata/sync/skycommand")
        assert sync_response.status_code == 200
        assert sync_response.json()["created"] == 6

        summary_response = client.get("/api/v1/metadata/summary")
        assert summary_response.status_code == 200
        assert summary_response.json()["assets"] == 7

        assets_response = client.get("/api/v1/metadata/assets?layer=RAW")
        assert assets_response.status_code == 200
        assert assets_response.json()["total"] == 7
    finally:
        app.dependency_overrides.clear()
