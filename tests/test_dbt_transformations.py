from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from skydata_studio.api.routes import dbt as dbt_route
from skydata_studio.db.session import get_session
from skydata_studio.main import app
from skydata_studio.schemas.dbt import DbtRelationSummary, DbtTransformationSummary
from sqlalchemy.orm import Session

client = TestClient(app)


def test_dbt_summary_endpoint_projects_layered_model_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = DbtTransformationSummary(
        model_count=3,
        ready_model_count=3,
        test_count=14,
        layers_ready=3,
        layer_count=3,
        relations=[
            DbtRelationSummary(
                name="Federal Funds Rate curated source",
                layer="SOURCE",
                relation="mart.fed_funds_rate",
                materialization="SOURCE",
                description="Curated source.",
                status="READY",
                row_count=26335,
            ),
            DbtRelationSummary(
                name="stg_fed_funds_rate",
                layer="STAGING",
                relation="dbt_staging.stg_fed_funds_rate",
                materialization="VIEW",
                description="Staging model.",
                status="READY",
                row_count=26335,
            ),
            DbtRelationSummary(
                name="int_fed_funds_rate_changes",
                layer="INTERMEDIATE",
                relation="dbt_intermediate.int_fed_funds_rate_changes",
                materialization="VIEW",
                description="Intermediate model.",
                status="READY",
                row_count=26335,
            ),
            DbtRelationSummary(
                name="fct_fed_funds_rate_daily",
                layer="MART",
                relation="dbt_mart.fct_fed_funds_rate_daily",
                materialization="TABLE",
                description="Mart model.",
                status="READY",
                row_count=26335,
            ),
        ],
    )

    def fake_summary(session: Session) -> DbtTransformationSummary:
        del session
        return expected

    def override_session() -> Generator[Session, None, None]:
        with Session() as session:
            yield session

    monkeypatch.setattr(dbt_route, "dbt_transformation_summary", fake_summary)
    app.dependency_overrides[get_session] = override_session
    try:
        response = client.get("/api/v1/transformations/dbt/summary")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"] == "DOCKER"
    assert payload["ready_model_count"] == 3
    assert payload["layers_ready"] == 3
    assert payload["relations"][-1]["relation"] == "dbt_mart.fct_fed_funds_rate_daily"
