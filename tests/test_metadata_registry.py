from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from skydata_studio.db.base import Base
from skydata_studio.db.session import get_session
from skydata_studio.integrations.skycommand.dependencies import get_skycommand_gateway
from skydata_studio.main import app
from skydata_studio.schemas.metadata import (
    MetadataAssetCreate,
    MetadataAssetFieldsReplace,
    MetadataAssetGovernanceUpdate,
    MetadataMappingCreate,
)
from skydata_studio.services.metadata_registry import (
    create_metadata_mapping,
    get_metadata_asset,
    get_metadata_mapping,
    list_metadata_assets,
    list_metadata_mappings,
    mapping_summary,
    metadata_summary,
    register_metadata_asset,
    replace_metadata_asset_fields,
    synchronize_skycommand_assets,
    update_metadata_asset_governance,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
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
            "code": "CUSTOMER_ACCOUNT_RAW",
            "name": "Customer Account Raw",
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


def _operations_mart() -> MetadataAssetCreate:
    return MetadataAssetCreate.model_validate(
        {
            "domain": {"code": "OPERATIONS", "name": "Operations"},
            "system": {"code": "ANALYTICS_WAREHOUSE", "name": "Analytics Warehouse"},
            "system_type": "WAREHOUSE",
            "namespace": {"code": "MART", "name": "Mart"},
            "code": "CUSTOMER_ACCOUNT",
            "name": "Customer Account",
            "asset_type": "TABLE",
            "layer": "MART",
            "physical_name": "dim_customer_account",
            "owner_name": "Data Engineering",
            "classification": "INTERNAL",
            "tags": ["Customer", "Mart"],
        }
    )


def _mapping_payload(source_id: str, target_id: str) -> MetadataMappingCreate:
    return MetadataMappingCreate.model_validate(
        {
            "code": "MAP_CUSTOMER_ACCOUNT_RAW_TO_MART",
            "name": "Customer account raw to mart",
            "source_asset_id": source_id,
            "target_asset_id": target_id,
            "mapping_type": "TRANSFORM",
            "load_strategy": "MERGE",
            "status": "READY",
            "grain": "One row per customer account",
            "business_keys": ["CUSTOMER_ID"],
            "description": "Standardizes the CRM account record for analytics.",
            "transformation_expression": "select customer_id, upper(account_status) ...",
            "field_mappings": [
                {
                    "source_field_code": "CUSTOMER_ID",
                    "target_field_code": "CUSTOMER_ID",
                    "target_data_type": "BIGINT",
                    "ordinal_position": 1,
                    "nullable": False,
                    "key_field": True,
                },
                {
                    "source_field_code": "ACCOUNT_STATUS",
                    "target_field_code": "ACCOUNT_STATUS",
                    "target_data_type": "VARCHAR(30)",
                    "transformation_type": "DERIVE",
                    "expression": "upper(ACCOUNT_STATUS)",
                    "ordinal_position": 2,
                },
            ],
        }
    )


def test_registry_persists_non_macro_product(registry_session: Session) -> None:
    created = register_metadata_asset(registry_session, _operations_asset())

    assert created.code == "CUSTOMER_ACCOUNT_RAW"
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
    assert get_metadata_asset(registry_session, created.id).name == "Customer Account Raw"


def test_registry_updates_governance_and_fields(registry_session: Session) -> None:
    created = register_metadata_asset(registry_session, _operations_mart())
    governed = update_metadata_asset_governance(
        registry_session,
        created.id,
        MetadataAssetGovernanceUpdate.model_validate(
            {
                "description": "Governed customer-account dimension.",
                "owner_name": "Analytics Engineering",
                "owner_email": "analytics@example.com",
                "classification": "CONFIDENTIAL",
                "criticality": "CRITICAL",
                "status": "ACTIVE",
                "tags": ["customer", "dimension"],
            }
        ),
    )
    assert governed.owner_name == "Analytics Engineering"
    assert governed.owner_email == "analytics@example.com"
    assert governed.criticality == "CRITICAL"

    with_fields = replace_metadata_asset_fields(
        registry_session,
        created.id,
        MetadataAssetFieldsReplace.model_validate(
            {
                "fields": [
                    {
                        "code": "CUSTOMER_ID",
                        "data_type": "BIGINT",
                        "nullable": False,
                        "key_field": True,
                    }
                ]
            }
        ),
    )
    assert with_fields.field_count == 1
    assert with_fields.fields[0].code == "CUSTOMER_ID"


def test_registry_creates_source_target_mapping(registry_session: Session) -> None:
    source = register_metadata_asset(registry_session, _operations_asset())
    target = register_metadata_asset(registry_session, _operations_mart())

    mapping = create_metadata_mapping(
        registry_session,
        _mapping_payload(source.id, target.id),
    )

    assert mapping.code == "MAP_CUSTOMER_ACCOUNT_RAW_TO_MART"
    assert mapping.source_asset.code == "CUSTOMER_ACCOUNT_RAW"
    assert mapping.target_asset.code == "CUSTOMER_ACCOUNT"
    assert mapping.load_strategy == "MERGE"
    assert mapping.business_keys == ["CUSTOMER_ID"]
    assert len(mapping.field_mappings) == 2

    target_detail = get_metadata_asset(registry_session, target.id)
    assert target_detail.field_count == 2
    assert len(target_detail.upstream_dependencies) == 1
    assert len(target_detail.inbound_mappings) == 1

    source_detail = get_metadata_asset(registry_session, source.id)
    assert len(source_detail.downstream_dependencies) == 1
    assert len(source_detail.outbound_mappings) == 1

    listed = list_metadata_mappings(registry_session, status="READY")
    assert listed.total == 1
    assert get_metadata_mapping(registry_session, mapping.id).field_mapping_count == 2

    summary = mapping_summary(registry_session)
    assert summary.mappings == 1
    assert summary.field_mappings == 2
    assert summary.dependencies == 1
    assert summary.statuses == {"READY": 1}
    assert summary.load_strategies == {"MERGE": 1}


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
        source_response = client.post(
            "/api/v1/metadata/assets",
            json=_operations_asset().model_dump(mode="json"),
        )
        assert source_response.status_code == 201
        source = source_response.json()

        target_response = client.post(
            "/api/v1/metadata/assets",
            json=_operations_mart().model_dump(mode="json"),
        )
        assert target_response.status_code == 201
        target = target_response.json()

        mapping_response = client.post(
            "/api/v1/metadata/mappings",
            json=_mapping_payload(source["id"], target["id"]).model_dump(mode="json"),
        )
        assert mapping_response.status_code == 201
        assert mapping_response.json()["field_mapping_count"] == 2

        mapping_summary_response = client.get("/api/v1/metadata/mappings/summary")
        assert mapping_summary_response.status_code == 200
        assert mapping_summary_response.json()["mappings"] == 1

        mapping_list_response = client.get("/api/v1/metadata/mappings?status=READY")
        assert mapping_list_response.status_code == 200
        assert mapping_list_response.json()["total"] == 1

        governance_response = client.patch(
            f"/api/v1/metadata/assets/{target['id']}/governance",
            json={
                "description": "Customer account mart.",
                "owner_name": "Data Platform",
                "owner_email": "platform@example.com",
                "classification": "INTERNAL",
                "criticality": "HIGH",
                "status": "ACTIVE",
                "tags": ["customer", "mart"],
            },
        )
        assert governance_response.status_code == 200
        assert governance_response.json()["owner_name"] == "Data Platform"

        fields_response = client.put(
            f"/api/v1/metadata/assets/{target['id']}/fields",
            json={
                "fields": [
                    {
                        "code": "CUSTOMER_ID",
                        "data_type": "BIGINT",
                        "ordinal_position": 1,
                        "nullable": False,
                        "key_field": True,
                    }
                ]
            },
        )
        assert fields_response.status_code == 200
        assert fields_response.json()["field_count"] == 1

        sync_response = client.post("/api/v1/metadata/sync/skycommand")
        assert sync_response.status_code == 200
        assert sync_response.json()["created"] == 6

        summary_response = client.get("/api/v1/metadata/summary")
        assert summary_response.status_code == 200
        assert summary_response.json()["assets"] == 8
        assert summary_response.json()["mappings"] == 1

        assets_response = client.get("/api/v1/metadata/assets?layer=RAW")
        assert assets_response.status_code == 200
        assert assets_response.json()["total"] == 7
    finally:
        app.dependency_overrides.clear()
