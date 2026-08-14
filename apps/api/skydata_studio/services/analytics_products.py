from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, cast

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from skydata_studio.schemas.analytics import (
    AnalyticsProductDefinition,
    AnalyticsProductSummary,
    AnalyticsPublicationGate,
    AnalyticsRelationEvidence,
)
from skydata_studio.schemas.dbt import (
    DbtModelCatalogueSummary,
    DbtSemanticLayerSummary,
)
from skydata_studio.schemas.lineage import AnalyticsConsumerLineageSummary
from skydata_studio.schemas.quality import QualityContractSummary
from skydata_studio.services.dbt_transformations import (
    dbt_model_catalogue,
    dbt_semantic_layer,
)
from skydata_studio.services.lineage_consumers import analytics_consumer_lineage_summary
from skydata_studio.services.quality_contracts import quality_contract_summary

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_product_path() -> Path:
    return (
        _repository_root()
        / "contracts"
        / "analytics"
        / "products"
        / "fed_funds_rate_daily_product.v1.json"
    )


def _consumer_contract_directory() -> Path:
    return _repository_root() / "contracts" / "analytics"


def _read_product(path: Path) -> AnalyticsProductDefinition:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected an object in analytical product contract {path}.")
    return AnalyticsProductDefinition.model_validate(cast(dict[str, Any], payload))


def _relation_parts(relation: str) -> tuple[str, str]:
    parts = relation.split(".")
    if len(parts) != 2 or not all(_IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(f"Unsafe analytical relation identifier: {relation!r}.")
    return parts[0], parts[1]


def _column_name(column: str) -> str:
    if not _IDENTIFIER.fullmatch(column):
        raise ValueError(f"Unsafe analytical freshness column: {column!r}.")
    return column


def _scalar_to_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def relation_evidence(
    session: Session,
    relation: str,
    freshness_column: str,
) -> AnalyticsRelationEvidence:
    schema, relation_name = _relation_parts(relation)
    column = _column_name(freshness_column)
    inspector = inspect(session.get_bind())
    if not inspector.has_table(relation_name, schema=schema):
        return AnalyticsRelationEvidence(relation=relation, status="MISSING")

    count_statement = text(f'SELECT COUNT(*) FROM "{schema}"."{relation_name}"')
    freshness_statement = text(
        f'SELECT MAX("{column}") FROM "{schema}"."{relation_name}"'
    )
    row_count = int(session.execute(count_statement).scalar_one())
    freshness_value = session.execute(freshness_statement).scalar_one()
    return AnalyticsRelationEvidence(
        relation=relation,
        status="READY",
        row_count=row_count,
        max_freshness_value=_scalar_to_text(freshness_value),
    )


def _model_build_status(
    product: AnalyticsProductDefinition,
    catalogue: DbtModelCatalogueSummary,
) -> Literal["READY", "ERROR", "UNKNOWN", "MISSING"]:
    model = next(
        (item for item in catalogue.models if item.relation == product.mart_relation),
        None,
    )
    if model is None:
        return "MISSING"
    return model.build_status


def _semantic_resolution(
    product: AnalyticsProductDefinition,
    semantic: DbtSemanticLayerSummary,
) -> tuple[bool, int]:
    semantic_model = next(
        (item for item in semantic.semantic_models if item.name == product.semantic_model),
        None,
    )
    if semantic_model is None or semantic.artifact_status != "READY":
        return False, 0

    available_dimensions = {item.name for item in semantic_model.dimensions}
    dimensions_ready = all(
        name in available_dimensions for name in product.required_dimensions
    )
    available_metrics = {
        item.name
        for item in semantic.metrics
        if item.semantic_model == product.semantic_model
    }
    resolved_metric_count = sum(
        metric_name in available_metrics for metric_name in product.required_metrics
    )
    return (
        dimensions_ready and resolved_metric_count == len(product.required_metrics),
        resolved_metric_count,
    )


def _consumer_resolution(
    product: AnalyticsProductDefinition,
    consumers: AnalyticsConsumerLineageSummary,
) -> tuple[int, int]:
    required_codes = set(product.consumer_codes)
    resolved_codes = {
        str(node.metadata.get("consumer_code") or "")
        for node in consumers.nodes
        if node.node_type == "ANALYTICS_CONSUMER" and node.status == "READY"
    }
    return len(required_codes), len(required_codes & resolved_codes)


def _freshness_status(
    product: AnalyticsProductDefinition,
    source: AnalyticsRelationEvidence,
    mart: AnalyticsRelationEvidence,
) -> Literal["ALIGNED", "STALE", "MISSING", "UNKNOWN"]:
    if source.status == "MISSING" or mart.status == "MISSING":
        return "MISSING"
    if source.row_count is None or mart.row_count is None:
        return "UNKNOWN"
    if source.max_freshness_value is None or mart.max_freshness_value is None:
        return "UNKNOWN"

    rows_aligned = source.row_count == mart.row_count
    dates_aligned = source.max_freshness_value == mart.max_freshness_value
    if product.row_alignment == "EXACT" and rows_aligned and dates_aligned:
        return "ALIGNED"
    return "STALE"


def _gate(
    code: str,
    label: str,
    status: Literal["PASS", "WARN", "BLOCK", "PENDING"],
    message: str,
) -> AnalyticsPublicationGate:
    return AnalyticsPublicationGate(
        code=code,
        label=label,
        status=status,
        message=message,
    )


def compose_analytics_product_summary(
    *,
    product: AnalyticsProductDefinition,
    source_path: str,
    source: AnalyticsRelationEvidence,
    mart: AnalyticsRelationEvidence,
    catalogue: DbtModelCatalogueSummary,
    semantic: DbtSemanticLayerSummary,
    quality: QualityContractSummary,
    consumers: AnalyticsConsumerLineageSummary,
) -> AnalyticsProductSummary:
    model_status = _model_build_status(product, catalogue)
    semantic_resolved, resolved_metric_count = _semantic_resolution(product, semantic)
    required_consumer_count, resolved_consumer_count = _consumer_resolution(product, consumers)
    freshness_status = _freshness_status(product, source, mart)

    row_count_delta = None
    if source.row_count is not None and mart.row_count is not None:
        row_count_delta = source.row_count - mart.row_count

    gates: list[AnalyticsPublicationGate] = []
    physical_ready = source.status == "READY" and mart.status == "READY"
    gates.append(
        _gate(
            "PHYSICAL_RELATIONS",
            "Source and mart relations exist",
            "PASS" if physical_ready else "BLOCK",
            (
                "Curated source and dbt analytical mart are both materialized."
                if physical_ready
                else "The curated source or dbt analytical mart relation is missing."
            ),
        )
    )

    model_gate_status: Literal["PASS", "WARN", "BLOCK", "PENDING"]
    if model_status == "READY":
        model_gate_status = "PASS"
    elif model_status == "UNKNOWN":
        model_gate_status = "PENDING"
    else:
        model_gate_status = "BLOCK"
    gates.append(
        _gate(
            "DBT_MODEL_BUILD",
            "dbt mart build evidence is green",
            model_gate_status,
            f"Latest dbt model status is {model_status}.",
        )
    )

    freshness_gate_status: Literal["PASS", "WARN", "BLOCK", "PENDING"]
    if freshness_status == "ALIGNED":
        freshness_gate_status = "PASS"
        freshness_message = (
            "Curated source and analytical mart have matching row counts and latest dates."
        )
    elif freshness_status == "STALE":
        freshness_gate_status = "BLOCK"
        freshness_message = (
            "Curated source is ahead of the analytical mart; run dbt build before publication."
        )
    elif freshness_status == "MISSING":
        freshness_gate_status = "BLOCK"
        freshness_message = "Freshness cannot be proven because a required relation is missing."
    else:
        freshness_gate_status = "PENDING"
        freshness_message = "Freshness evidence is incomplete."
    gates.append(
        _gate(
            "FRESHNESS_ALIGNMENT",
            "Curated source and dbt mart are synchronized",
            freshness_gate_status,
            freshness_message,
        )
    )

    quality_matches = quality.contract_code == product.quality_contract_code
    quality_pass = quality_matches and quality.contract_status == "COMPLIANT"
    quality_gate_status: Literal["PASS", "WARN", "BLOCK", "PENDING"]
    if quality_pass:
        quality_gate_status = "PASS"
    elif quality.contract_status == "PENDING":
        quality_gate_status = "PENDING"
    else:
        quality_gate_status = "BLOCK"
    gates.append(
        _gate(
            "QUALITY_CONTRACT",
            "Quality contract permits consumption",
            quality_gate_status,
            (
                "Required quality contract is COMPLIANT."
                if quality_pass
                else (
                    "Required quality contract does not match the analytical product."
                    if not quality_matches
                    else f"Quality contract is {quality.contract_status}."
                )
            ),
        )
    )

    semantic_gate_status: Literal["PASS", "WARN", "BLOCK", "PENDING"]
    if semantic_resolved:
        semantic_gate_status = "PASS"
    elif semantic.artifact_status == "READY":
        semantic_gate_status = "BLOCK"
    else:
        semantic_gate_status = "PENDING"
    gates.append(
        _gate(
            "SEMANTIC_PRODUCT",
            "Semantic model and governed metrics resolve",
            semantic_gate_status,
            (
                f"Resolved {resolved_metric_count}/"
                f"{len(product.required_metrics)} required metrics."
            ),
        )
    )

    consumer_ready = (
        required_consumer_count > 0
        and resolved_consumer_count == required_consumer_count
    )
    consumer_gate_status: Literal["PASS", "WARN", "BLOCK", "PENDING"]
    if consumer_ready:
        consumer_gate_status = "PASS"
    elif consumers.consumer_status == "MISSING":
        consumer_gate_status = "BLOCK"
    else:
        consumer_gate_status = "PENDING"
    gates.append(
        _gate(
            "DECLARED_CONSUMERS",
            "Declared consumers resolve to governed semantics",
            consumer_gate_status,
            f"Resolved {resolved_consumer_count}/{required_consumer_count} required consumers.",
        )
    )

    blocking_codes = {item.code for item in gates if item.status == "BLOCK"}
    pending = any(item.status == "PENDING" for item in gates)
    if not physical_ready:
        product_status: Literal["READY", "STALE", "BLOCKED", "PENDING", "MISSING"] = (
            "MISSING"
        )
    elif "FRESHNESS_ALIGNMENT" in blocking_codes:
        product_status = "STALE"
    elif blocking_codes:
        product_status = "BLOCKED"
    elif pending:
        product_status = "PENDING"
    else:
        product_status = "READY"

    if product_status == "READY":
        publication_message = (
            "Analytical product is synchronized, governed, semantically resolved, "
            "and ready for delivery."
        )
    elif product_status == "STALE":
        publication_message = (
            "Analytical product is structurally healthy but stale relative to the curated source. "
            "Run dbt build, then refresh this workbench."
        )
    elif product_status == "BLOCKED":
        publication_message = "Analytical publication is blocked by one or more governance gates."
    elif product_status == "MISSING":
        publication_message = "Analytical publication is missing required physical data products."
    else:
        publication_message = "Analytical publication is waiting for complete runtime evidence."

    return AnalyticsProductSummary(
        product_status=product_status,
        product_code=product.code,
        product_version=product.version,
        product_name=product.name,
        description=product.description,
        owner=product.owner,
        domain=product.domain,
        source_path=source_path,
        source_relation=source,
        mart_relation=mart,
        row_count_delta=row_count_delta,
        freshness_status=freshness_status,
        refresh_required=product_status == "STALE",
        model_build_status=model_status,
        semantic_artifact_status=semantic.artifact_status,
        semantic_model_resolved=semantic_resolved,
        quality_contract_status=quality.contract_status,
        required_metric_count=len(product.required_metrics),
        resolved_metric_count=resolved_metric_count,
        required_consumer_count=required_consumer_count,
        resolved_consumer_count=resolved_consumer_count,
        gates=gates,
        publication_message=publication_message,
    )


def analytics_product_summary(
    session: Session,
    *,
    product_path: Path | None = None,
    target_dir: Path | None = None,
    consumer_contract_directory: Path | None = None,
) -> AnalyticsProductSummary:
    path = product_path or _default_product_path()
    product = _read_product(path)
    try:
        source_path = path.relative_to(_repository_root()).as_posix()
    except ValueError:
        source_path = path.as_posix()

    source = relation_evidence(session, product.source_relation, product.freshness_column)
    mart = relation_evidence(session, product.mart_relation, product.freshness_column)
    catalogue = dbt_model_catalogue(target_dir)
    semantic = dbt_semantic_layer(target_dir)
    quality = quality_contract_summary(target_dir=target_dir)
    consumers = analytics_consumer_lineage_summary(
        contract_directory=consumer_contract_directory or _consumer_contract_directory(),
        target_dir=target_dir,
    )
    return compose_analytics_product_summary(
        product=product,
        source_path=source_path,
        source=source,
        mart=mart,
        catalogue=catalogue,
        semantic=semantic,
        quality=quality,
        consumers=consumers,
    )
