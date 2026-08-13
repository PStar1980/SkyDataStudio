from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

from skydata_studio.schemas.dbt import DbtSemanticLayerSummary
from skydata_studio.schemas.lineage import (
    AnalyticsConsumerDefinition,
    AnalyticsConsumerEdge,
    AnalyticsConsumerImpactSummary,
    AnalyticsConsumerLineageSummary,
    AnalyticsConsumerMetricBinding,
    AnalyticsConsumerNode,
)
from skydata_studio.services.dbt_transformations import dbt_semantic_layer


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _contract_directory() -> Path:
    return _repository_root() / "contracts" / "analytics"


def _read_consumer(path: Path) -> AnalyticsConsumerDefinition:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected an object in analytics consumer contract {path}.")
    return AnalyticsConsumerDefinition.model_validate(cast(dict[str, Any], payload))


def _read_consumers(
    directory: Path | None = None,
) -> tuple[list[AnalyticsConsumerDefinition], list[str]]:
    root = directory or _contract_directory()
    if not root.exists():
        return [], []
    paths = sorted(root.glob("*.json"))
    consumers = [_read_consumer(path) for path in paths]
    source_paths: list[str] = []
    for path in paths:
        try:
            source_paths.append(path.relative_to(_repository_root()).as_posix())
        except ValueError:
            source_paths.append(path.as_posix())
    return consumers, source_paths


def _consumer_node_id(code: str) -> str:
    return f"consumer:{code.lower()}"


def _metric_node_id(unique_id: str) -> str:
    return f"metric:{unique_id}"


def _impact_from_graph(
    *,
    metric_name: str | None,
    nodes: list[AnalyticsConsumerNode],
    edges: list[AnalyticsConsumerEdge],
) -> AnalyticsConsumerImpactSummary:
    metric_nodes = {
        str(node.metadata.get("metric_name") or ""): node
        for node in nodes
        if node.node_type == "METRIC"
    }
    selected_name = metric_name if metric_name in metric_nodes else None
    if selected_name is None and metric_nodes:
        selected_name = sorted(metric_nodes)[0]
    if selected_name is None:
        return AnalyticsConsumerImpactSummary()

    selected = metric_nodes[selected_name]
    downstream_ids = {
        edge.downstream_id for edge in edges if edge.upstream_id == selected.id
    }
    consumers = [
        node
        for node in nodes
        if node.node_type == "ANALYTICS_CONSUMER" and node.id in downstream_ids
    ]
    consumers.sort(key=lambda item: item.label)
    return AnalyticsConsumerImpactSummary(
        selected_metric_name=selected_name,
        selected_metric_label=selected.label,
        downstream_consumer_count=len(consumers),
        consumers=consumers,
    )


def compose_consumer_lineage_summary(
    *,
    consumers: list[AnalyticsConsumerDefinition],
    semantic: DbtSemanticLayerSummary,
    source_paths: list[str] | None = None,
    focus_metric_name: str | None = None,
) -> AnalyticsConsumerLineageSummary:
    metric_by_name = {metric.name: metric for metric in semantic.metrics}
    semantic_model_by_name = {model.name: model for model in semantic.semantic_models}
    nodes_by_id: dict[str, AnalyticsConsumerNode] = {}
    edges: list[AnalyticsConsumerEdge] = []
    bindings: list[AnalyticsConsumerMetricBinding] = []
    resolved_consumers = 0
    declared_metric_count = 0
    resolved_metric_count = 0

    for consumer in consumers:
        declared_metric_count += len(consumer.required_metrics)
        semantic_model = semantic_model_by_name.get(consumer.semantic_model)
        available_dimensions = {
            dimension.name for dimension in semantic_model.dimensions
        } if semantic_model is not None else set()
        dimensions_ready = all(
            dimension in available_dimensions for dimension in consumer.required_dimensions
        )
        consumer_metrics_ready = True
        consumer_node_id = _consumer_node_id(consumer.code)
        nodes_by_id[consumer_node_id] = AnalyticsConsumerNode(
            id=consumer_node_id,
            label=consumer.name,
            node_type="ANALYTICS_CONSUMER",
            system=consumer.delivery_system,
            status="DECLARED",
            metadata={
                "consumer_code": consumer.code,
                "consumer_type": consumer.consumer_type,
                "deployment_status": consumer.deployment_status,
                "semantic_model": consumer.semantic_model,
                "owner": consumer.owner,
                "required_dimensions": len(consumer.required_dimensions),
            },
        )

        for metric_name in consumer.required_metrics:
            metric = metric_by_name.get(metric_name)
            resolved = (
                semantic.artifact_status == "READY"
                and semantic_model is not None
                and metric is not None
                and metric.semantic_model == consumer.semantic_model
            )
            bindings.append(
                AnalyticsConsumerMetricBinding(
                    consumer_code=consumer.code,
                    metric_name=metric_name,
                    metric_label=metric.label if metric is not None else None,
                    metric_unique_id=metric.unique_id if metric is not None else None,
                    resolved=resolved,
                    message=(
                        "Governed metric resolves to the declared semantic consumer."
                        if resolved
                        else "Declared metric is not available on the required semantic model."
                    ),
                )
            )
            if not resolved or metric is None:
                consumer_metrics_ready = False
                continue

            resolved_metric_count += 1
            metric_node_id = _metric_node_id(metric.unique_id)
            nodes_by_id.setdefault(
                metric_node_id,
                AnalyticsConsumerNode(
                    id=metric_node_id,
                    label=metric.label,
                    node_type="METRIC",
                    system="dbt semantic",
                    status="READY",
                    metadata={
                        "metric_name": metric.name,
                        "metric_type": metric.metric_type,
                        "semantic_model": metric.semantic_model,
                    },
                ),
            )
            edges.append(
                AnalyticsConsumerEdge(
                    id=f"consumer-metric:{metric_node_id}:{consumer_node_id}",
                    upstream_id=metric_node_id,
                    downstream_id=consumer_node_id,
                    edge_type="CONSUMED_BY",
                    label="declared report dependency",
                )
            )

        if (
            semantic.artifact_status == "READY"
            and semantic_model is not None
            and dimensions_ready
            and consumer_metrics_ready
        ):
            resolved_consumers += 1
            nodes_by_id[consumer_node_id].status = "READY"

    unresolved_metric_count = declared_metric_count - resolved_metric_count
    if consumers and resolved_consumers == len(consumers) and not unresolved_metric_count:
        consumer_status: Literal["READY", "PARTIAL", "MISSING"] = "READY"
    elif consumers or nodes_by_id:
        consumer_status = "PARTIAL"
    else:
        consumer_status = "MISSING"

    nodes = sorted(
        nodes_by_id.values(),
        key=lambda item: (item.node_type == "ANALYTICS_CONSUMER", item.label),
    )
    default_impact = _impact_from_graph(
        metric_name=focus_metric_name,
        nodes=nodes,
        edges=edges,
    )
    return AnalyticsConsumerLineageSummary(
        consumer_status=consumer_status,
        semantic_artifact_status=semantic.artifact_status,
        consumer_contract_count=len(consumers),
        resolved_consumer_count=resolved_consumers,
        declared_metric_count=declared_metric_count,
        resolved_metric_count=resolved_metric_count,
        unresolved_metric_count=unresolved_metric_count,
        node_count=len(nodes),
        edge_count=len(edges),
        source_paths=source_paths or [],
        consumers=consumers,
        metric_bindings=bindings,
        nodes=nodes,
        edges=edges,
        default_impact=default_impact,
    )


def analytics_consumer_lineage_summary(
    *,
    focus_metric_name: str | None = None,
    contract_directory: Path | None = None,
    target_dir: Path | None = None,
) -> AnalyticsConsumerLineageSummary:
    consumers, source_paths = _read_consumers(contract_directory)
    return compose_consumer_lineage_summary(
        consumers=consumers,
        semantic=dbt_semantic_layer(target_dir),
        source_paths=source_paths,
        focus_metric_name=focus_metric_name,
    )


def analytics_consumer_impact(
    metric_name: str,
    *,
    contract_directory: Path | None = None,
    target_dir: Path | None = None,
) -> AnalyticsConsumerImpactSummary:
    summary = analytics_consumer_lineage_summary(
        focus_metric_name=metric_name,
        contract_directory=contract_directory,
        target_dir=target_dir,
    )
    return summary.default_impact
