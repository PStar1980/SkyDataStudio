from dataclasses import dataclass
from typing import Literal

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from skydata_studio.schemas.dbt import DbtRelationSummary, DbtTransformationSummary


@dataclass(frozen=True)
class _ExpectedRelation:
    name: str
    layer: Literal["SOURCE", "STAGING", "INTERMEDIATE", "MART"]
    schema: str
    relation_name: str
    materialization: Literal["TABLE", "VIEW", "SOURCE"]
    description: str

    @property
    def qualified_name(self) -> str:
        return f"{self.schema}.{self.relation_name}"


_EXPECTED_RELATIONS = (
    _ExpectedRelation(
        name="Federal Funds Rate curated source",
        layer="SOURCE",
        schema="mart",
        relation_name="fed_funds_rate",
        materialization="SOURCE",
        description="Phase 4.3 curated DFF table used as the governed dbt source seam.",
    ),
    _ExpectedRelation(
        name="stg_fed_funds_rate",
        layer="STAGING",
        schema="dbt_staging",
        relation_name="stg_fed_funds_rate",
        materialization="VIEW",
        description="Typed and renamed Federal Funds Rate staging model.",
    ),
    _ExpectedRelation(
        name="int_fed_funds_rate_changes",
        layer="INTERMEDIATE",
        schema="dbt_intermediate",
        relation_name="int_fed_funds_rate_changes",
        materialization="VIEW",
        description="Reusable change and period attributes derived from the staged rate series.",
    ),
    _ExpectedRelation(
        name="fct_fed_funds_rate_daily",
        layer="MART",
        schema="dbt_mart",
        relation_name="fct_fed_funds_rate_daily",
        materialization="TABLE",
        description="Consumer-ready daily Federal Funds Rate fact model.",
    ),
)


def _relation_exists(session: Session, relation: _ExpectedRelation) -> bool:
    inspector = inspect(session.get_bind())
    return inspector.has_table(relation.relation_name, schema=relation.schema)


def _row_count(session: Session, relation: _ExpectedRelation) -> int:
    statement = text(
        f'SELECT COUNT(*) FROM "{relation.schema}"."{relation.relation_name}"'
    )
    return int(session.execute(statement).scalar_one())


def dbt_transformation_summary(session: Session) -> DbtTransformationSummary:
    relations: list[DbtRelationSummary] = []

    for relation in _EXPECTED_RELATIONS:
        exists = _relation_exists(session, relation)
        relations.append(
            DbtRelationSummary(
                name=relation.name,
                layer=relation.layer,
                relation=relation.qualified_name,
                materialization=relation.materialization,
                description=relation.description,
                status="READY" if exists else "MISSING",
                row_count=_row_count(session, relation) if exists else None,
            )
        )

    model_relations = [relation for relation in relations if relation.layer != "SOURCE"]
    ready_model_count = sum(relation.status == "READY" for relation in model_relations)
    ready_layers = {relation.layer for relation in model_relations if relation.status == "READY"}

    return DbtTransformationSummary(
        model_count=len(model_relations),
        ready_model_count=ready_model_count,
        test_count=14,
        layers_ready=len(ready_layers),
        layer_count=3,
        relations=relations,
    )
