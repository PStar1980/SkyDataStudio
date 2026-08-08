from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from skydata_studio.db.base import Base
from skydata_studio.db.session import get_session
from skydata_studio.main import app
from skydata_studio.schemas.execution import PipelineRunRequest
from skydata_studio.schemas.metadata import MetadataAssetCreate, MetadataMappingCreate
from skydata_studio.schemas.pipelines import PipelineDefinitionCreate
from skydata_studio.services.metadata_registry import (
    create_metadata_mapping,
    register_metadata_asset,
)
from skydata_studio.services.pipeline_execution import (
    execute_pipeline,
    get_pipeline_run,
    list_pipeline_runs,
    pipeline_run_summary,
)
from skydata_studio.services.pipeline_registry import (
    create_pipeline,
    get_pipeline,
    list_pipelines,
    pipeline_summary,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def pipeline_session() -> Generator[Session, None, None]:
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


def _asset(*, code: str, name: str, layer: str, system: str, namespace: str) -> MetadataAssetCreate:
    return MetadataAssetCreate.model_validate(
        {
            "domain": {"code": "MACRO", "name": "Macroeconomic Data"},
            "system": {"code": system, "name": system.replace("_", " ").title()},
            "namespace": {"code": namespace, "name": namespace.title()},
            "code": code,
            "name": name,
            "asset_type": "TABLE",
            "layer": layer,
            "physical_name": code.lower(),
            "owner_name": "Data Engineering",
            "classification": "INTERNAL",
        }
    )


def _mapping(session: Session) -> tuple[str, str, str]:
    source = register_metadata_asset(
        session,
        _asset(
            code="DFF",
            name="Federal Funds Effective Rate",
            layer="RAW",
            system="SKYCOMMAND",
            namespace="MACRO",
        ),
    )
    target = register_metadata_asset(
        session,
        _asset(
            code="FED_FUNDS_RATE_MART",
            name="Federal Funds Rate Mart",
            layer="MART",
            system="SKYDATA",
            namespace="MART",
        ),
    )
    mapping = create_metadata_mapping(
        session,
        MetadataMappingCreate.model_validate(
            {
                "code": "MAP_DFF_TO_FED_FUNDS_RATE_MART",
                "name": "DFF to Federal Funds Rate Mart",
                "source_asset_id": source.id,
                "target_asset_id": target.id,
                "mapping_type": "TRANSFORM",
                "load_strategy": "MERGE",
                "status": "READY",
                "business_keys": ["OBSERVATION_DATE"],
                "field_mappings": [
                    {
                        "source_field_code": "OBSERVATION_DATE",
                        "target_field_code": "OBSERVATION_DATE",
                        "target_data_type": "DATE",
                        "nullable": False,
                        "key_field": True,
                    },
                    {
                        "source_field_code": "VALUE",
                        "target_field_code": "RATE",
                        "target_data_type": "NUMERIC(10,4)",
                        "transformation_type": "CAST",
                    },
                ],
            }
        ),
    )
    return mapping.id, source.id, target.id


def _pipeline_payload(mapping_id: str) -> PipelineDefinitionCreate:
    return PipelineDefinitionCreate.model_validate(
        {
            "code": "FED_FUNDS_RATE_PIPELINE",
            "name": "Federal Funds Rate Pipeline",
            "description": "Transforms trusted DFF data into the curated rate mart.",
            "status": "READY",
            "environment": "development",
            "mapping_id": mapping_id,
            "parameters": [
                {
                    "code": "RUN_DATE",
                    "name": "Run date",
                    "data_type": "DATE",
                    "required": False,
                    "ordinal_position": 1,
                }
            ],
            "steps": [
                {
                    "code": "READ_SOURCE",
                    "name": "Read trusted source",
                    "step_type": "SQL",
                    "execution_order": 1,
                    "sql_text": "select * from macro.dff",
                },
                {
                    "code": "TRANSFORM_MART",
                    "name": "Transform mart",
                    "step_type": "SQL",
                    "execution_order": 2,
                    "depends_on_codes": ["READ_SOURCE"],
                },
                {
                    "code": "VALIDATE_TARGET",
                    "name": "Validate target",
                    "step_type": "VALIDATION",
                    "execution_order": 3,
                    "depends_on_codes": ["TRANSFORM_MART"],
                },
                {
                    "code": "PUBLISH_TARGET",
                    "name": "Publish target",
                    "step_type": "PUBLISH",
                    "execution_order": 4,
                    "depends_on_codes": ["VALIDATE_TARGET"],
                },
            ],
        }
    )


def test_pipeline_definition_persists_versioned_graph(pipeline_session: Session) -> None:
    mapping_id, source_id, target_id = _mapping(pipeline_session)
    created = create_pipeline(pipeline_session, _pipeline_payload(mapping_id))

    assert created.code == "FED_FUNDS_RATE_PIPELINE"
    assert created.current_version == 1
    assert created.version_count == 1
    assert created.parameter_count == 1
    assert created.step_count == 4
    assert created.mapping is not None
    assert created.mapping.code == "MAP_DFF_TO_FED_FUNDS_RATE_MART"

    version = created.versions[0]
    assert version.status == "READY"
    assert [step.code for step in version.steps] == [
        "READ_SOURCE",
        "TRANSFORM_MART",
        "VALIDATE_TARGET",
        "PUBLISH_TARGET",
    ]
    assert version.steps[1].dependencies[0].depends_on_step_code == "READ_SOURCE"
    assert version.steps[1].source_asset_id == source_id
    assert version.steps[1].target_asset_id == target_id

    summary = pipeline_summary(pipeline_session)
    assert summary.pipelines == 1
    assert summary.versions == 1
    assert summary.parameters == 1
    assert summary.steps == 4
    assert summary.dependencies == 3
    assert summary.statuses == {"READY": 1}

    listed = list_pipelines(pipeline_session, status="READY")
    assert listed.total == 1
    assert get_pipeline(pipeline_session, created.id).step_count == 4


def test_pipeline_api_exposes_summary_list_detail_and_create(pipeline_session: Session) -> None:
    mapping_id, _, _ = _mapping(pipeline_session)

    def override_session() -> Generator[Session, None, None]:
        yield pipeline_session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        create_response = client.post(
            "/api/v1/pipelines",
            json=_pipeline_payload(mapping_id).model_dump(mode="json"),
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["code"] == "FED_FUNDS_RATE_PIPELINE"
        assert created["step_count"] == 4

        summary_response = client.get("/api/v1/pipelines/summary")
        assert summary_response.status_code == 200
        assert summary_response.json()["dependencies"] == 3

        list_response = client.get("/api/v1/pipelines?status=READY")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        detail_response = client.get(f"/api/v1/pipelines/{created['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["versions"][0]["steps"][3]["code"] == "PUBLISH_TARGET"
    finally:
        app.dependency_overrides.clear()


def test_local_execution_persists_structured_replay_safe_run_evidence(
    pipeline_session: Session,
) -> None:
    mapping_id, _, _ = _mapping(pipeline_session)
    pipeline = create_pipeline(pipeline_session, _pipeline_payload(mapping_id))

    first = execute_pipeline(
        pipeline_session,
        PipelineRunRequest(
            pipeline_id=pipeline.id,
            parameters={"RUN_DATE": "2026-08-08"},
        ),
    )

    assert first.reused is False
    assert first.run.status == "SUCCEEDED"
    assert first.run.parameters == {"RUN_DATE": "2026-08-08"}
    assert first.run.step_count == 4
    assert first.run.succeeded_steps == 4
    assert first.run.failed_steps == 0
    assert first.run.result["data_mutation_applied"] is False
    assert [step.step_code for step in first.run.step_runs] == [
        "READ_SOURCE",
        "TRANSFORM_MART",
        "VALIDATE_TARGET",
        "PUBLISH_TARGET",
    ]
    assert first.run.step_runs[0].result["operation"] == "READ_CONTRACT_PROBE"
    assert (
        first.run.step_runs[2].result["operation"]
        == "TARGET_CONTRACT_VALIDATION"
    )
    assert (
        first.run.step_runs[3].result["publication_status"]
        == "ELIGIBLE_NOT_PUBLISHED"
    )

    replay = execute_pipeline(
        pipeline_session,
        PipelineRunRequest(
            pipeline_id=pipeline.id,
            parameters={"RUN_DATE": "2026-08-08"},
        ),
    )
    assert replay.reused is True
    assert replay.run.id == first.run.id
    assert replay.run.replay_count == 1

    forced = execute_pipeline(
        pipeline_session,
        PipelineRunRequest(
            pipeline_id=pipeline.id,
            parameters={"RUN_DATE": "2026-08-08"},
            replay_mode="FORCE_NEW",
        ),
    )
    assert forced.reused is False
    assert forced.run.id != first.run.id

    summary = pipeline_run_summary(pipeline_session)
    assert summary.runs == 2
    assert summary.step_runs == 8
    assert summary.replayed_runs == 1
    assert summary.statuses == {"SUCCEEDED": 2}

    listed = list_pipeline_runs(pipeline_session, pipeline_id=pipeline.id)
    assert listed.total == 2
    assert get_pipeline_run(pipeline_session, first.run.id).run_key == first.run.run_key


def test_pipeline_run_api_exposes_execution_summary_history_and_detail(
    pipeline_session: Session,
) -> None:
    mapping_id, _, _ = _mapping(pipeline_session)
    pipeline = create_pipeline(pipeline_session, _pipeline_payload(mapping_id))

    def override_session() -> Generator[Session, None, None]:
        yield pipeline_session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        run_response = client.post(
            "/api/v1/pipeline-runs",
            json={
                "pipeline_id": pipeline.id,
                "parameters": {"RUN_DATE": "2026-08-08"},
            },
        )
        assert run_response.status_code == 201
        run_payload = run_response.json()
        assert run_payload["reused"] is False
        assert run_payload["run"]["status"] == "SUCCEEDED"
        assert run_payload["run"]["step_count"] == 4

        summary_response = client.get("/api/v1/pipeline-runs/summary")
        assert summary_response.status_code == 200
        assert summary_response.json()["runs"] == 1
        assert summary_response.json()["step_runs"] == 4

        list_response = client.get(
            f"/api/v1/pipeline-runs?pipeline_id={pipeline.id}&status=SUCCEEDED"
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        run_id = run_payload["run"]["id"]
        detail_response = client.get(f"/api/v1/pipeline-runs/{run_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["pipeline_code"] == "FED_FUNDS_RATE_PIPELINE"
        assert detail["step_runs"][3]["step_code"] == "PUBLISH_TARGET"

        replay_response = client.post(
            "/api/v1/pipeline-runs",
            json={
                "pipeline_id": pipeline.id,
                "parameters": {"RUN_DATE": "2026-08-08"},
            },
        )
        assert replay_response.status_code == 201
        assert replay_response.json()["reused"] is True
        assert replay_response.json()["run"]["replay_count"] == 1
    finally:
        app.dependency_overrides.clear()
