import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from skydata_studio.schemas.dbt import (
    DbtModelCatalogueItem,
    DbtModelCatalogueSummary,
    DbtModelColumnSummary,
    DbtModelDependencySummary,
    DbtRelationSummary,
    DbtTransformationSummary,
)


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


def _default_dbt_target_dir() -> Path:
    repository_root = Path(__file__).resolve().parents[4]
    return repository_root / "transformations" / "dbt" / "skydata_studio" / "target"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected an object in dbt artifact {path}.")
    return cast(dict[str, Any], payload)


def _model_layer(node: dict[str, Any]) -> Literal["STAGING", "INTERMEDIATE", "MART"]:
    schema = str(node.get("schema") or "").lower()
    original_path = str(node.get("original_file_path") or "").lower()
    if schema == "dbt_staging" or "/staging/" in f"/{original_path}":
        return "STAGING"
    if schema == "dbt_intermediate" or "/intermediate/" in f"/{original_path}":
        return "INTERMEDIATE"
    return "MART"


def _materialization(node: dict[str, Any]) -> Literal["TABLE", "VIEW"]:
    config = node.get("config")
    value = config.get("materialized") if isinstance(config, dict) else None
    return "VIEW" if str(value).lower() == "view" else "TABLE"


def _dependency_summary(
    unique_id: str,
    nodes: dict[str, Any],
    sources: dict[str, Any],
) -> DbtModelDependencySummary | None:
    dependency = nodes.get(unique_id)
    resource_type: Literal["MODEL", "SOURCE"] = "MODEL"
    if dependency is None:
        dependency = sources.get(unique_id)
        resource_type = "SOURCE"
    if not isinstance(dependency, dict):
        return None
    return DbtModelDependencySummary(
        unique_id=unique_id,
        name=str(dependency.get("name") or unique_id),
        resource_type=resource_type,
    )


def _run_statuses(run_results: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    results = run_results.get("results")
    if not isinstance(results, list):
        return statuses
    for result in results:
        if not isinstance(result, dict):
            continue
        unique_id = result.get("unique_id")
        status = result.get("status")
        if isinstance(unique_id, str) and isinstance(status, str):
            statuses[unique_id] = status.lower()
    return statuses


def _build_status(unique_id: str, statuses: dict[str, str]) -> Literal["READY", "ERROR", "UNKNOWN"]:
    status = statuses.get(unique_id)
    if status in {"success", "pass"}:
        return "READY"
    if status in {"error", "fail", "runtime error"}:
        return "ERROR"
    return "UNKNOWN"


def dbt_model_catalogue(target_dir: Path | None = None) -> DbtModelCatalogueSummary:
    target = target_dir or _default_dbt_target_dir()
    manifest_path = target / "manifest.json"
    if not manifest_path.exists():
        return DbtModelCatalogueSummary(
            artifact_status="MISSING",
            model_count=0,
            ready_model_count=0,
            source_count=0,
            test_count=0,
            models=[],
        )

    manifest = _read_json(manifest_path)
    run_results_path = target / "run_results.json"
    run_results = _read_json(run_results_path) if run_results_path.exists() else {}
    statuses = _run_statuses(run_results)

    raw_nodes = manifest.get("nodes")
    raw_sources = manifest.get("sources")
    nodes = cast(dict[str, Any], raw_nodes) if isinstance(raw_nodes, dict) else {}
    sources = cast(dict[str, Any], raw_sources) if isinstance(raw_sources, dict) else {}

    model_nodes = {
        unique_id: node
        for unique_id, node in nodes.items()
        if isinstance(node, dict)
        and node.get("resource_type") == "model"
        and node.get("package_name") == "skydata_studio"
        and bool((node.get("config") or {}).get("enabled", True))
    }
    test_nodes = [
        node
        for node in nodes.values()
        if isinstance(node, dict)
        and node.get("resource_type") == "test"
        and node.get("package_name") == "skydata_studio"
    ]

    models: list[DbtModelCatalogueItem] = []
    for unique_id, node in sorted(
        model_nodes.items(),
        key=lambda item: (
            {"STAGING": 1, "INTERMEDIATE": 2, "MART": 3}[_model_layer(item[1])],
            str(item[1].get("name") or ""),
        ),
    ):
        depends_on = node.get("depends_on")
        upstream_ids = depends_on.get("nodes", []) if isinstance(depends_on, dict) else []
        upstream = [
            summary
            for dependency_id in upstream_ids
            if isinstance(dependency_id, str)
            if (summary := _dependency_summary(dependency_id, nodes, sources)) is not None
        ]

        downstream: list[DbtModelDependencySummary] = []
        for candidate_id, candidate in model_nodes.items():
            candidate_depends_on = candidate.get("depends_on")
            candidate_nodes = (
                candidate_depends_on.get("nodes", [])
                if isinstance(candidate_depends_on, dict)
                else []
            )
            if unique_id in candidate_nodes:
                summary = _dependency_summary(candidate_id, nodes, sources)
                if summary is not None:
                    downstream.append(summary)

        columns_payload = node.get("columns")
        columns = []
        if isinstance(columns_payload, dict):
            for column_name, column_payload in columns_payload.items():
                description = None
                if isinstance(column_payload, dict):
                    raw_description = column_payload.get("description")
                    if isinstance(raw_description, str) and raw_description.strip():
                        description = raw_description
                columns.append(
                    DbtModelColumnSummary(name=str(column_name), description=description)
                )

        test_count = 0
        for test_node in test_nodes:
            test_depends_on = test_node.get("depends_on")
            dependency_ids = (
                test_depends_on.get("nodes", []) if isinstance(test_depends_on, dict) else []
            )
            if unique_id in dependency_ids:
                test_count += 1

        relation_schema = str(node.get("schema") or "")
        relation_alias = str(node.get("alias") or node.get("name") or "")
        tags = [str(tag) for tag in node.get("tags", []) if isinstance(tag, str)]
        models.append(
            DbtModelCatalogueItem(
                unique_id=unique_id,
                name=str(node.get("name") or unique_id),
                layer=_model_layer(node),
                relation=f"{relation_schema}.{relation_alias}",
                materialization=_materialization(node),
                description=(str(node.get("description")) if node.get("description") else None),
                build_status=_build_status(unique_id, statuses),
                path=str(node.get("original_file_path") or node.get("path") or ""),
                tags=tags,
                columns=columns,
                upstream=upstream,
                downstream=downstream,
                test_count=test_count,
            )
        )

    metadata = manifest.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    ready_model_count = sum(model.build_status == "READY" for model in models)

    return DbtModelCatalogueSummary(
        artifact_status="READY",
        generated_at=(
            str(metadata.get("generated_at")) if metadata.get("generated_at") else None
        ),
        dbt_version=str(metadata.get("dbt_version")) if metadata.get("dbt_version") else None,
        model_count=len(models),
        ready_model_count=ready_model_count,
        source_count=len(sources),
        test_count=len(test_nodes),
        models=models,
    )
