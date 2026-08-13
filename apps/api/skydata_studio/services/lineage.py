from __future__ import annotations

from collections import deque
from typing import Literal

from sqlalchemy.orm import Session

from skydata_studio.schemas.dbt import DbtModelCatalogueSummary, DbtSemanticLayerSummary
from skydata_studio.schemas.lineage import (
    FieldLineageEdge,
    FieldLineageImpactSummary,
    FieldLineageNode,
    FieldLineageSummary,
    LineageEdge,
    LineageImpactSummary,
    LineageNode,
    LineageSummary,
)
from skydata_studio.services.dbt_transformations import dbt_model_catalogue, dbt_semantic_layer
from skydata_studio.services.metadata_registry import (
    get_metadata_mapping,
    list_metadata_mappings,
)


def _canonical_name(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    for suffix in ("_mart", "_table", "_view", "_dataset"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized


def _metadata_node_id(asset_id: str) -> str:
    return f"metadata:{asset_id}"


def _dbt_node_id(unique_id: str) -> str:
    return f"dbt:{unique_id}"


def _semantic_node_id(unique_id: str) -> str:
    return f"semantic:{unique_id}"


def _metric_node_id(unique_id: str) -> str:
    return f"metric:{unique_id}"


def _impact_from_graph(
    nodes: list[LineageNode],
    edges: list[LineageEdge],
    selected_node_id: str | None,
) -> LineageImpactSummary:
    node_by_id = {node.id: node for node in nodes}
    if selected_node_id not in node_by_id:
        selected_node_id = None

    if selected_node_id is None:
        preferred = next(
            (node.id for node in nodes if node.node_type == "SOURCE_ASSET"),
            None,
        )
        selected_node_id = preferred or (nodes[0].id if nodes else None)

    if selected_node_id is None:
        return LineageImpactSummary(
            downstream_node_count=0,
            affected_model_count=0,
            affected_semantic_model_count=0,
            affected_metric_count=0,
            affected_layers=[],
            nodes=[],
        )

    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.upstream_id, []).append(edge.downstream_id)

    visited: set[str] = set()
    queue: deque[str] = deque(adjacency.get(selected_node_id, []))
    while queue:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        queue.extend(adjacency.get(node_id, []))

    impacted = [node for node in nodes if node.id in visited]
    affected_layers = sorted({str(node.layer) for node in impacted})
    return LineageImpactSummary(
        selected_node_id=selected_node_id,
        selected_node_label=node_by_id[selected_node_id].label,
        downstream_node_count=len(impacted),
        affected_model_count=sum(node.node_type == "DBT_MODEL" for node in impacted),
        affected_semantic_model_count=sum(
            node.node_type == "SEMANTIC_MODEL" for node in impacted
        ),
        affected_metric_count=sum(node.node_type == "METRIC" for node in impacted),
        affected_layers=affected_layers,
        nodes=impacted,
    )


def compose_lineage_summary(
    session: Session,
    *,
    catalogue: DbtModelCatalogueSummary,
    semantic: DbtSemanticLayerSummary,
    focus_node_id: str | None = None,
) -> LineageSummary:
    nodes: list[LineageNode] = []
    edges: list[LineageEdge] = []
    node_ids: set[str] = set()

    def add_node(node: LineageNode) -> None:
        if node.id in node_ids:
            return
        node_ids.add(node.id)
        nodes.append(node)

    mappings = list_metadata_mappings(session, status="READY", limit=500, offset=0)
    target_nodes_by_canonical: dict[str, str] = {}
    for mapping in mappings.items:
        source_id = _metadata_node_id(mapping.source_asset.id)
        target_id = _metadata_node_id(mapping.target_asset.id)
        add_node(
            LineageNode(
                id=source_id,
                label=mapping.source_asset.code,
                node_type="SOURCE_ASSET",
                layer="RAW",
                system=mapping.source_asset.system_code,
                relation=mapping.source_asset.code,
                description=mapping.source_asset.name,
                status="READY",
                metadata={
                    "mapping_code": mapping.code,
                    "mapping_type": mapping.mapping_type,
                    "field_mappings": mapping.field_mapping_count,
                },
            )
        )
        add_node(
            LineageNode(
                id=target_id,
                label=mapping.target_asset.code,
                node_type="CURATED_ASSET",
                layer="MART",
                system=mapping.target_asset.system_code,
                relation=mapping.target_asset.code,
                description=mapping.target_asset.name,
                status="READY",
                metadata={
                    "mapping_code": mapping.code,
                    "load_strategy": mapping.load_strategy,
                    "field_mappings": mapping.field_mapping_count,
                },
            )
        )
        edges.append(
            LineageEdge(
                id=f"mapping:{mapping.id}",
                upstream_id=source_id,
                downstream_id=target_id,
                edge_type="MAPPING",
                label=f"{mapping.mapping_type} · {mapping.load_strategy}",
            )
        )
        target_nodes_by_canonical[_canonical_name(mapping.target_asset.code)] = target_id

    dependency_nodes: dict[str, str] = {}
    for model in catalogue.models:
        for dependency in model.upstream:
            if dependency.resource_type != "SOURCE":
                continue
            node_id = _dbt_node_id(dependency.unique_id)
            dependency_nodes[dependency.unique_id] = node_id
            add_node(
                LineageNode(
                    id=node_id,
                    label=dependency.name,
                    node_type="DBT_SOURCE",
                    layer="SOURCE",
                    system="dbt",
                    relation=f"mart.{dependency.name}",
                    description="Governed dbt source seam over Studio-curated data.",
                    status="READY" if catalogue.artifact_status == "READY" else "MISSING",
                    metadata={"unique_id": dependency.unique_id},
                )
            )
            upstream_metadata_id = target_nodes_by_canonical.get(
                _canonical_name(dependency.name)
            )
            if upstream_metadata_id:
                edge_id = f"publish:{upstream_metadata_id}:{node_id}"
                if not any(edge.id == edge_id for edge in edges):
                    edges.append(
                        LineageEdge(
                            id=edge_id,
                            upstream_id=upstream_metadata_id,
                            downstream_id=node_id,
                            edge_type="PUBLISHES_AS",
                            label="curated relation → dbt source",
                        )
                    )

    model_node_ids: dict[str, str] = {}
    for model in catalogue.models:
        node_id = _dbt_node_id(model.unique_id)
        model_node_ids[model.unique_id] = node_id
        add_node(
            LineageNode(
                id=node_id,
                label=model.name,
                node_type="DBT_MODEL",
                layer=model.layer,
                system="dbt",
                relation=model.relation,
                description=model.description,
                status="READY" if model.build_status == "READY" else "UNKNOWN",
                metadata={
                    "materialization": model.materialization,
                    "test_count": model.test_count,
                    "path": model.path,
                },
            )
        )

    for model in catalogue.models:
        downstream_id = model_node_ids[model.unique_id]
        for dependency in model.upstream:
            upstream_id = (
                model_node_ids.get(dependency.unique_id)
                if dependency.resource_type == "MODEL"
                else dependency_nodes.get(dependency.unique_id)
            )
            if upstream_id is None:
                continue
            edges.append(
                LineageEdge(
                    id=f"depends:{upstream_id}:{downstream_id}",
                    upstream_id=upstream_id,
                    downstream_id=downstream_id,
                    edge_type="DEPENDS_ON",
                    label="dbt depends_on",
                )
            )

    semantic_nodes_by_name: dict[str, str] = {}
    model_nodes_by_relation = {
        model.relation.lower(): model_node_ids[model.unique_id]
        for model in catalogue.models
    }
    for semantic_model in semantic.semantic_models:
        node_id = _semantic_node_id(semantic_model.unique_id)
        semantic_nodes_by_name[semantic_model.name] = node_id
        add_node(
            LineageNode(
                id=node_id,
                label=semantic_model.name,
                node_type="SEMANTIC_MODEL",
                layer="SEMANTIC",
                system="dbt semantic",
                relation=semantic_model.relation,
                description=semantic_model.description,
                status="READY" if semantic.artifact_status == "READY" else "MISSING",
                metadata={
                    "entities": len(semantic_model.entities),
                    "dimensions": len(semantic_model.dimensions),
                    "metrics": len(semantic_model.metric_names),
                },
            )
        )
        if semantic_model.relation:
            upstream_id = model_nodes_by_relation.get(semantic_model.relation.lower())
            if upstream_id:
                edges.append(
                    LineageEdge(
                        id=f"semantic:{upstream_id}:{node_id}",
                        upstream_id=upstream_id,
                        downstream_id=node_id,
                        edge_type="SEMANTIC_OF",
                        label="semantic model over mart",
                    )
                )

    for metric in semantic.metrics:
        node_id = _metric_node_id(metric.unique_id)
        add_node(
            LineageNode(
                id=node_id,
                label=metric.label or metric.name,
                node_type="METRIC",
                layer="METRIC",
                system="dbt semantic",
                description=metric.description,
                status="READY" if semantic.artifact_status == "READY" else "MISSING",
                metadata={
                    "metric_name": metric.name,
                    "metric_type": metric.metric_type,
                    "time_dimension": metric.time_dimension,
                },
            )
        )
        upstream_id = (
            semantic_nodes_by_name.get(metric.semantic_model)
            if metric.semantic_model
            else None
        )
        if upstream_id:
            edges.append(
                LineageEdge(
                    id=f"metric:{upstream_id}:{node_id}",
                    upstream_id=upstream_id,
                    downstream_id=node_id,
                    edge_type="METRIC_OF",
                    label="governed metric",
                )
            )

    artifact_status: Literal["READY", "PARTIAL", "MISSING"]
    if catalogue.artifact_status == "READY" and semantic.artifact_status == "READY":
        artifact_status = "READY"
    elif nodes:
        artifact_status = "PARTIAL"
    else:
        artifact_status = "MISSING"

    default_impact = _impact_from_graph(nodes, edges, focus_node_id)
    return LineageSummary(
        artifact_status=artifact_status,
        metadata_mapping_count=mappings.total,
        dbt_model_count=catalogue.model_count,
        semantic_model_count=semantic.semantic_model_count,
        metric_count=semantic.metric_count,
        node_count=len(nodes),
        edge_count=len(edges),
        nodes=nodes,
        edges=edges,
        default_impact=default_impact,
    )


def lineage_summary(
    session: Session,
    *,
    focus_node_id: str | None = None,
) -> LineageSummary:
    return compose_lineage_summary(
        session,
        catalogue=dbt_model_catalogue(),
        semantic=dbt_semantic_layer(),
        focus_node_id=focus_node_id,
    )


def lineage_impact(session: Session, node_id: str) -> LineageImpactSummary:
    summary = lineage_summary(session, focus_node_id=node_id)
    return summary.default_impact



def _field_node_id(parent_id: str, field_name: str) -> str:
    return f"field:{parent_id}:{field_name.strip().lower()}"


def _field_impact_from_graph(
    nodes: list[FieldLineageNode],
    edges: list[FieldLineageEdge],
    selected_field_id: str | None,
) -> FieldLineageImpactSummary:
    node_by_id = {node.id: node for node in nodes}
    if selected_field_id not in node_by_id:
        selected_field_id = None

    if selected_field_id is None:
        preferred = next(
            (node.id for node in nodes if node.node_type == "SOURCE_FIELD"),
            None,
        )
        selected_field_id = preferred or (nodes[0].id if nodes else None)

    if selected_field_id is None:
        return FieldLineageImpactSummary(
            downstream_node_count=0,
            affected_field_count=0,
            affected_metric_count=0,
            affected_relations=[],
            affected_layers=[],
            nodes=[],
        )

    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.upstream_id, []).append(edge.downstream_id)

    visited: set[str] = set()
    queue: deque[str] = deque(adjacency.get(selected_field_id, []))
    while queue:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        queue.extend(adjacency.get(node_id, []))

    impacted = [node for node in nodes if node.id in visited]
    return FieldLineageImpactSummary(
        selected_field_id=selected_field_id,
        selected_field_label=node_by_id[selected_field_id].label,
        downstream_node_count=len(impacted),
        affected_field_count=sum(node.node_type != "METRIC" for node in impacted),
        affected_metric_count=sum(node.node_type == "METRIC" for node in impacted),
        affected_relations=sorted(
            {node.relation for node in impacted if node.relation is not None}
        ),
        affected_layers=sorted({str(node.layer) for node in impacted}),
        nodes=impacted,
    )


def _parse_lineage_input(reference: str) -> tuple[str, str, str] | None:
    kind, separator, remainder = reference.partition(":")
    if not separator or kind not in {"source", "model"}:
        return None
    parent, dot, field_name = remainder.rpartition(".")
    if not dot or not parent or not field_name:
        return None
    return kind, parent, field_name


def compose_field_lineage_summary(
    session: Session,
    *,
    catalogue: DbtModelCatalogueSummary,
    semantic: DbtSemanticLayerSummary,
    focus_field_id: str | None = None,
) -> FieldLineageSummary:
    nodes: list[FieldLineageNode] = []
    edges: list[FieldLineageEdge] = []
    node_ids: set[str] = set()
    edge_ids: set[str] = set()

    def add_node(node: FieldLineageNode) -> None:
        if node.id in node_ids:
            return
        node_ids.add(node.id)
        nodes.append(node)

    def add_edge(edge: FieldLineageEdge) -> None:
        if edge.id in edge_ids:
            return
        edge_ids.add(edge.id)
        edges.append(edge)

    mappings = list_metadata_mappings(session, status="READY", limit=500, offset=0)
    target_fields_by_canonical: dict[tuple[str, str], str] = {}
    field_mapping_count = 0

    for mapping_item in mappings.items:
        mapping = get_metadata_mapping(session, mapping_item.id)
        source_parent_id = _metadata_node_id(mapping.source_asset.id)
        target_parent_id = _metadata_node_id(mapping.target_asset.id)
        target_canonical = _canonical_name(mapping.target_asset.code)

        for field_mapping in mapping.field_mappings:
            if field_mapping.source_field_code is None:
                continue
            field_mapping_count += 1
            source_field = field_mapping.source_field_code.lower()
            target_field = field_mapping.target_field_code.lower()
            source_id = _field_node_id(source_parent_id, source_field)
            target_id = _field_node_id(target_parent_id, target_field)

            add_node(
                FieldLineageNode(
                    id=source_id,
                    label=f"{mapping.source_asset.code}.{source_field}",
                    field_name=source_field,
                    node_type="SOURCE_FIELD",
                    layer="RAW",
                    system=mapping.source_asset.system_code,
                    relation=mapping.source_asset.code,
                    parent_node_id=source_parent_id,
                    parent_label=mapping.source_asset.code,
                    status="READY",
                    metadata={
                        "mapping_code": mapping.code,
                        "transformation_type": field_mapping.transformation_type,
                    },
                )
            )
            add_node(
                FieldLineageNode(
                    id=target_id,
                    label=f"{mapping.target_asset.code}.{target_field}",
                    field_name=target_field,
                    node_type="CURATED_FIELD",
                    layer="MART",
                    system=mapping.target_asset.system_code,
                    relation=mapping.target_asset.code,
                    parent_node_id=target_parent_id,
                    parent_label=mapping.target_asset.code,
                    description=field_mapping.description,
                    status="READY",
                    metadata={
                        "target_data_type": field_mapping.target_data_type,
                        "transformation_type": field_mapping.transformation_type,
                    },
                )
            )
            add_edge(
                FieldLineageEdge(
                    id=f"field-mapping:{field_mapping.id}",
                    upstream_id=source_id,
                    downstream_id=target_id,
                    edge_type="FIELD_MAPPING",
                    label=field_mapping.transformation_type,
                )
            )
            target_fields_by_canonical[(target_canonical, target_field)] = target_id

    source_field_ids: dict[tuple[str, str], str] = {}
    source_unique_ids: dict[str, str] = {}
    for model in catalogue.models:
        for dependency in model.upstream:
            if dependency.resource_type == "SOURCE":
                source_unique_ids.setdefault(dependency.name, dependency.unique_id)

    for source_name, unique_id in source_unique_ids.items():
        canonical = _canonical_name(source_name)
        for (
            target_canonical,
            field_name,
        ), published_upstream_id in target_fields_by_canonical.items():
            if target_canonical != canonical:
                continue
            parent_id = _dbt_node_id(unique_id)
            node_id = _field_node_id(parent_id, field_name)
            source_field_ids[(source_name, field_name)] = node_id
            add_node(
                FieldLineageNode(
                    id=node_id,
                    label=f"{source_name}.{field_name}",
                    field_name=field_name,
                    node_type="DBT_SOURCE_FIELD",
                    layer="SOURCE",
                    system="dbt",
                    relation=f"mart.{source_name}",
                    parent_node_id=parent_id,
                    parent_label=source_name,
                    status="READY" if catalogue.artifact_status == "READY" else "MISSING",
                    metadata={"unique_id": unique_id},
                )
            )
            add_edge(
                FieldLineageEdge(
                    id=f"field-publish:{published_upstream_id}:{node_id}",
                    upstream_id=published_upstream_id,
                    downstream_id=node_id,
                    edge_type="PUBLISHES_AS",
                    label="curated field → dbt source field",
                )
            )

    model_by_name = {model.name: model for model in catalogue.models}
    model_field_ids: dict[tuple[str, str], str] = {}
    dbt_annotated_column_count = 0

    for model in catalogue.models:
        parent_id = _dbt_node_id(model.unique_id)
        for column in model.columns:
            if not column.lineage_inputs:
                continue
            dbt_annotated_column_count += 1
            field_name = column.name.lower()
            node_id = _field_node_id(parent_id, field_name)
            model_field_ids[(model.name, field_name)] = node_id
            add_node(
                FieldLineageNode(
                    id=node_id,
                    label=f"{model.name}.{field_name}",
                    field_name=field_name,
                    node_type="DBT_MODEL_FIELD",
                    layer=model.layer,
                    system="dbt",
                    relation=model.relation,
                    parent_node_id=parent_id,
                    parent_label=model.name,
                    description=column.description,
                    status="READY" if model.build_status == "READY" else "UNKNOWN",
                    metadata={
                        "materialization": model.materialization,
                        "lineage_inputs": len(column.lineage_inputs),
                    },
                )
            )

    for model in catalogue.models:
        for column in model.columns:
            downstream_id = model_field_ids.get((model.name, column.name.lower()))
            if downstream_id is None:
                continue
            for reference in column.lineage_inputs:
                parsed = _parse_lineage_input(reference)
                if parsed is None:
                    continue
                kind, parent_name, field_name = parsed
                lineage_upstream_id: str | None = None
                if kind == "source":
                    source_name = parent_name.split(".")[-1]
                    lineage_upstream_id = source_field_ids.get(
                        (source_name, field_name.lower())
                    )
                else:
                    upstream_model = model_by_name.get(parent_name)
                    if upstream_model is not None:
                        lineage_upstream_id = model_field_ids.get(
                            (upstream_model.name, field_name.lower())
                        )
                if lineage_upstream_id is None:
                    continue
                add_edge(
                    FieldLineageEdge(
                        id=f"field-derive:{lineage_upstream_id}:{downstream_id}",
                        upstream_id=lineage_upstream_id,
                        downstream_id=downstream_id,
                        edge_type="DERIVES",
                        label="dbt column lineage",
                    )
                )

    semantic_model_by_name = {model.name: model for model in semantic.semantic_models}
    model_by_relation = {model.relation.lower(): model for model in catalogue.models}
    metric_binding_count = 0
    for metric in semantic.metrics:
        semantic_model = (
            semantic_model_by_name.get(metric.semantic_model)
            if metric.semantic_model
            else None
        )
        if semantic_model is None or semantic_model.relation is None or not metric.expression:
            continue
        mart_model = model_by_relation.get(semantic_model.relation.lower())
        if mart_model is None:
            continue
        metric_upstream_id = model_field_ids.get(
            (mart_model.name, metric.expression.lower())
        )
        if metric_upstream_id is None:
            continue
        metric_binding_count += 1
        metric_parent_id = _metric_node_id(metric.unique_id)
        metric_id = _field_node_id(metric_parent_id, metric.name)
        add_node(
            FieldLineageNode(
                id=metric_id,
                label=metric.label or metric.name,
                field_name=metric.name,
                node_type="METRIC",
                layer="METRIC",
                system="dbt semantic",
                parent_node_id=metric_parent_id,
                parent_label=metric.semantic_model,
                description=metric.description,
                status="READY" if semantic.artifact_status == "READY" else "MISSING",
                metadata={
                    "expression": metric.expression,
                    "aggregation": metric.aggregation,
                    "time_dimension": metric.time_dimension,
                },
            )
        )
        add_edge(
            FieldLineageEdge(
                id=f"field-metric:{metric_upstream_id}:{metric_id}",
                upstream_id=metric_upstream_id,
                downstream_id=metric_id,
                edge_type="FEEDS_METRIC",
                label=f"{metric.aggregation or metric.metric_type}({metric.expression})",
            )
        )

    artifact_status: Literal["READY", "PARTIAL", "MISSING"]
    if (
        catalogue.artifact_status == "READY"
        and semantic.artifact_status == "READY"
        and field_mapping_count > 0
        and dbt_annotated_column_count > 0
    ):
        artifact_status = "READY"
    elif nodes:
        artifact_status = "PARTIAL"
    else:
        artifact_status = "MISSING"

    default_impact = _field_impact_from_graph(nodes, edges, focus_field_id)
    return FieldLineageSummary(
        artifact_status=artifact_status,
        field_mapping_count=field_mapping_count,
        dbt_annotated_column_count=dbt_annotated_column_count,
        metric_binding_count=metric_binding_count,
        node_count=len(nodes),
        edge_count=len(edges),
        nodes=nodes,
        edges=edges,
        default_impact=default_impact,
    )


def field_lineage_summary(
    session: Session,
    *,
    focus_field_id: str | None = None,
) -> FieldLineageSummary:
    return compose_field_lineage_summary(
        session,
        catalogue=dbt_model_catalogue(),
        semantic=dbt_semantic_layer(),
        focus_field_id=focus_field_id,
    )


def field_lineage_impact(session: Session, field_id: str) -> FieldLineageImpactSummary:
    summary = field_lineage_summary(session, focus_field_id=field_id)
    return summary.default_impact
