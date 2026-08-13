from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from skydata_studio.core.config import Settings
from skydata_studio.integrations.airflow import AirflowClient, AirflowClientError
from skydata_studio.models.pipeline import PipelineDefinition, PipelineRun
from skydata_studio.schemas.airflow import AirflowDagRunDetail, AirflowTaskInstanceSummary
from skydata_studio.schemas.execution import PipelineRunRead
from skydata_studio.schemas.lineage import (
    LineageSummary,
    RuntimeLineageEdge,
    RuntimeLineageEdgeType,
    RuntimeLineageNode,
    RuntimeLineageNodeType,
    RuntimeLineageSummary,
)
from skydata_studio.services.lineage import lineage_summary
from skydata_studio.services.pipeline_execution import get_pipeline_run

PROOF_DAG_ID = "skydata_studio_fed_funds_rate_pipeline"
PROOF_PIPELINE_CODE = "FED_FUNDS_RATE_PIPELINE"
_AIRFLOW_TASK_ORDER = {
    "resolve_pipeline_contract": 1,
    "execute_studio_pipeline": 2,
    "validate_materialization": 3,
    "publish_batch_evidence": 4,
}


def _airflow_client(settings: Settings) -> AirflowClient:
    return AirflowClient(
        api_base_url=settings.airflow_api_base_url,
        auth_mode=settings.airflow_api_auth_mode,
        timeout_seconds=settings.airflow_api_timeout_seconds,
        username=settings.airflow_api_username,
        password=settings.airflow_api_password,
        token=settings.airflow_api_token,
    )


def _latest_airflow_pipeline_run(session: Session) -> PipelineRunRead | None:
    run_id = session.scalar(
        select(PipelineRun.id)
        .join(PipelineDefinition, PipelineRun.pipeline_id == PipelineDefinition.id)
        .where(
            PipelineRun.trigger_type == "AIRFLOW",
            PipelineRun.run_key.like("AIRFLOW:%"),
            PipelineDefinition.code == PROOF_PIPELINE_CODE,
        )
        .order_by(PipelineRun.created_at.desc())
        .limit(1)
    )
    return get_pipeline_run(session, run_id) if run_id is not None else None


def _airflow_dag_run_id(run: PipelineRunRead | None) -> str | None:
    if run is None or not run.run_key.startswith("AIRFLOW:"):
        return None
    value = run.run_key.removeprefix("AIRFLOW:").strip()
    return value or None


def _runtime_node(
    *,
    node_id: str,
    label: str,
    node_type: RuntimeLineageNodeType,
    system: str,
    status: str,
    relation: str | None = None,
    metadata: dict[str, object] | None = None,
) -> RuntimeLineageNode:
    return RuntimeLineageNode(
        id=node_id,
        label=label,
        node_type=node_type,
        system=system,
        status=status,
        relation=relation,
        metadata=metadata or {},
    )


def _edge(
    *,
    edge_id: str,
    upstream_id: str,
    downstream_id: str,
    edge_type: RuntimeLineageEdgeType,
    label: str,
) -> RuntimeLineageEdge:
    return RuntimeLineageEdge(
        id=edge_id,
        upstream_id=upstream_id,
        downstream_id=downstream_id,
        edge_type=edge_type,
        label=label,
    )


def _ordered_airflow_tasks(
    tasks: Iterable[AirflowTaskInstanceSummary],
) -> list[AirflowTaskInstanceSummary]:
    return sorted(
        tasks,
        key=lambda item: (
            _AIRFLOW_TASK_ORDER.get(item.task_id, 99),
            item.start_date is None,
            item.start_date,
            item.task_id,
        ),
    )


def _safe_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def compose_runtime_lineage_summary(
    *,
    asset_lineage: LineageSummary,
    studio_run: PipelineRunRead | None,
    airflow_detail: AirflowDagRunDetail | None,
    airflow_error: str | None = None,
) -> RuntimeLineageSummary:
    nodes: list[RuntimeLineageNode] = []
    edges: list[RuntimeLineageEdge] = []

    source_node = next(
        (node for node in asset_lineage.nodes if node.node_type == "SOURCE_ASSET"),
        None,
    )
    target_node = next(
        (node for node in asset_lineage.nodes if node.node_type == "CURATED_ASSET"),
        None,
    )

    if source_node is not None:
        nodes.append(
            _runtime_node(
                node_id=source_node.id,
                label=source_node.label,
                node_type="STRUCTURAL_ASSET",
                system=source_node.system,
                status=source_node.status,
                relation=source_node.relation,
                metadata={"role": "SOURCE"},
            )
        )
    if target_node is not None:
        nodes.append(
            _runtime_node(
                node_id=target_node.id,
                label=target_node.label,
                node_type="STRUCTURAL_ASSET",
                system=target_node.system,
                status=target_node.status,
                relation=target_node.relation,
                metadata={"role": "TARGET"},
            )
        )

    if studio_run is None:
        return RuntimeLineageSummary(
            runtime_status="MISSING",
            airflow_connection_status="UNKNOWN",
            pipeline_code=PROOF_PIPELINE_CODE,
            dag_id=PROOF_DAG_ID,
            airflow_error=airflow_error,
            node_count=len(nodes),
            edge_count=0,
            nodes=nodes,
            edges=[],
        )

    pipeline_node_id = f"pipeline:{studio_run.pipeline_id}"
    dag_node_id = f"airflow:dag:{PROOF_DAG_ID}"
    dag_run_id = _airflow_dag_run_id(studio_run)
    dag_run_node_id = (
        f"airflow:dag-run:{dag_run_id}" if dag_run_id else "airflow:dag-run:unknown"
    )
    studio_run_node_id = f"studio-run:{studio_run.id}"

    nodes.extend(
        [
            _runtime_node(
                node_id=pipeline_node_id,
                label=studio_run.pipeline_name,
                node_type="PIPELINE_DEFINITION",
                system="SkyData Studio",
                status="READY",
                metadata={
                    "pipeline_code": studio_run.pipeline_code,
                    "version_number": studio_run.version_number,
                    "environment": studio_run.environment,
                },
            ),
            _runtime_node(
                node_id=dag_node_id,
                label=PROOF_DAG_ID,
                node_type="AIRFLOW_DAG",
                system="Apache Airflow",
                status="READY" if airflow_detail is not None else "UNKNOWN",
                metadata={"pipeline_code": studio_run.pipeline_code},
            ),
            _runtime_node(
                node_id=dag_run_node_id,
                label=dag_run_id or "Airflow run unavailable",
                node_type="AIRFLOW_DAG_RUN",
                system="Apache Airflow",
                status=(airflow_detail.run.state if airflow_detail is not None else "UNKNOWN"),
                metadata={
                    "run_type": airflow_detail.run.run_type if airflow_detail else None,
                    "logical_date": (
                        airflow_detail.run.logical_date.isoformat()
                        if airflow_detail and airflow_detail.run.logical_date
                        else None
                    ),
                },
            ),
            _runtime_node(
                node_id=studio_run_node_id,
                label=studio_run.run_key,
                node_type="STUDIO_PIPELINE_RUN",
                system="SkyData Studio",
                status=studio_run.status,
                relation=str(studio_run.result.get("target_relation") or "") or None,
                metadata={
                    "replay_count": studio_run.replay_count,
                    "trigger_type": studio_run.trigger_type,
                    "run_date": studio_run.parameters.get("RUN_DATE"),
                },
            ),
        ]
    )

    if source_node is not None:
        edges.append(
            _edge(
                edge_id=f"runtime-read:{source_node.id}:{pipeline_node_id}",
                upstream_id=source_node.id,
                downstream_id=pipeline_node_id,
                edge_type="READS_FROM",
                label="pipeline source",
            )
        )
    edges.extend(
        [
            _edge(
                edge_id=f"runtime-orchestrates:{pipeline_node_id}:{dag_node_id}",
                upstream_id=pipeline_node_id,
                downstream_id=dag_node_id,
                edge_type="ORCHESTRATED_BY",
                label="Airflow control plane",
            ),
            _edge(
                edge_id=f"runtime-execution:{dag_node_id}:{dag_run_node_id}",
                upstream_id=dag_node_id,
                downstream_id=dag_run_node_id,
                edge_type="EXECUTION",
                label="latest linked DAG run",
            ),
        ]
    )

    airflow_tasks = _ordered_airflow_tasks(airflow_detail.tasks if airflow_detail else [])
    airflow_task_node_ids: list[str] = []
    for task in airflow_tasks:
        task_node_id = f"airflow:task:{dag_run_id or 'unknown'}:{task.task_id}"
        airflow_task_node_ids.append(task_node_id)
        nodes.append(
            _runtime_node(
                node_id=task_node_id,
                label=task.task_display_name or task.task_id,
                node_type="AIRFLOW_TASK",
                system="Apache Airflow",
                status=task.state,
                metadata={
                    "task_id": task.task_id,
                    "try_number": task.try_number,
                    "duration_seconds": task.duration,
                    "operator": task.operator,
                },
            )
        )

    if airflow_task_node_ids:
        edges.append(
            _edge(
                edge_id=f"runtime-task-start:{dag_run_node_id}:{airflow_task_node_ids[0]}",
                upstream_id=dag_run_node_id,
                downstream_id=airflow_task_node_ids[0],
                edge_type="TASK_FLOW",
                label="Airflow task order",
            )
        )
        for upstream_id, downstream_id in zip(
            airflow_task_node_ids,
            airflow_task_node_ids[1:],
            strict=False,
        ):
            edges.append(
                _edge(
                    edge_id=f"runtime-task:{upstream_id}:{downstream_id}",
                    upstream_id=upstream_id,
                    downstream_id=downstream_id,
                    edge_type="TASK_FLOW",
                    label="Airflow dependency",
                )
            )

    execute_task_id = next(
        (
            node_id
            for node_id, task in zip(airflow_task_node_ids, airflow_tasks, strict=False)
            if task.task_id == "execute_studio_pipeline"
        ),
        None,
    )
    edges.append(
        _edge(
            edge_id=f"runtime-callback:{execute_task_id or dag_run_node_id}:{studio_run_node_id}",
            upstream_id=execute_task_id or dag_run_node_id,
            downstream_id=studio_run_node_id,
            edge_type="CALLS_STUDIO",
            label="public pipeline-runs API",
        )
    )

    studio_step_node_ids: list[str] = []
    for step in sorted(studio_run.step_runs, key=lambda item: item.execution_order):
        step_node_id = f"studio-step:{step.id}"
        studio_step_node_ids.append(step_node_id)
        nodes.append(
            _runtime_node(
                node_id=step_node_id,
                label=step.step_code,
                node_type="STUDIO_STEP_RUN",
                system="SkyData Studio",
                status=step.status,
                metadata={
                    "step_name": step.step_name,
                    "step_type": step.step_type,
                    "execution_order": step.execution_order,
                    "attempt_count": step.attempt_count,
                    "duration_ms": step.duration_ms,
                },
            )
        )

    if studio_step_node_ids:
        edges.append(
            _edge(
                edge_id=f"runtime-step-start:{studio_run_node_id}:{studio_step_node_ids[0]}",
                upstream_id=studio_run_node_id,
                downstream_id=studio_step_node_ids[0],
                edge_type="STEP_FLOW",
                label="Studio step order",
            )
        )
        for upstream_id, downstream_id in zip(
            studio_step_node_ids,
            studio_step_node_ids[1:],
            strict=False,
        ):
            edges.append(
                _edge(
                    edge_id=f"runtime-step:{upstream_id}:{downstream_id}",
                    upstream_id=upstream_id,
                    downstream_id=downstream_id,
                    edge_type="STEP_FLOW",
                    label="pipeline dependency",
                )
            )
        if target_node is not None:
            edges.append(
                _edge(
                    edge_id=f"runtime-materializes:{studio_step_node_ids[-1]}:{target_node.id}",
                    upstream_id=studio_step_node_ids[-1],
                    downstream_id=target_node.id,
                    edge_type="MATERIALIZES",
                    label="curated target publication",
                )
            )

    expected_airflow_tasks = len(_AIRFLOW_TASK_ORDER)
    expected_studio_steps = 4
    if (
        airflow_detail is not None
        and source_node is not None
        and target_node is not None
        and len(airflow_tasks) == expected_airflow_tasks
        and len(studio_run.step_runs) == expected_studio_steps
    ):
        runtime_status: Literal["READY", "PARTIAL", "MISSING"] = "READY"
    else:
        runtime_status = "PARTIAL"

    result = studio_run.result
    target_row_count = _safe_int(result.get("target_row_count"))
    return RuntimeLineageSummary(
        runtime_status=runtime_status,
        airflow_connection_status=(
            "CONNECTED" if airflow_detail is not None else "UNAVAILABLE"
        ),
        pipeline_code=studio_run.pipeline_code,
        dag_id=PROOF_DAG_ID,
        dag_run_id=dag_run_id,
        studio_run_id=studio_run.id,
        studio_run_key=studio_run.run_key,
        airflow_dag_run_status=(airflow_detail.run.state if airflow_detail else None),
        studio_run_status=studio_run.status,
        airflow_task_count=len(airflow_tasks),
        successful_airflow_task_count=sum(
            task.state.lower() == "success" for task in airflow_tasks
        ),
        studio_step_count=len(studio_run.step_runs),
        succeeded_studio_step_count=sum(
            step.status == "SUCCEEDED" for step in studio_run.step_runs
        ),
        replay_count=studio_run.replay_count,
        materialization_executed=result.get("materialization_executed") is True,
        data_mutation_applied=result.get("data_mutation_applied") is True,
        target_relation=str(result.get("target_relation") or "") or None,
        target_row_count=target_row_count,
        airflow_error=airflow_error,
        node_count=len(nodes),
        edge_count=len(edges),
        nodes=nodes,
        edges=edges,
    )


def runtime_lineage_summary(session: Session, settings: Settings) -> RuntimeLineageSummary:
    studio_run = _latest_airflow_pipeline_run(session)
    dag_run_id = _airflow_dag_run_id(studio_run)
    airflow_detail: AirflowDagRunDetail | None = None
    airflow_error: str | None = None

    if dag_run_id is not None:
        try:
            airflow_detail = _airflow_client(settings).dag_run_detail(
                PROOF_DAG_ID,
                dag_run_id,
            )
        except AirflowClientError as error:
            airflow_error = str(error)

    return compose_runtime_lineage_summary(
        asset_lineage=lineage_summary(session),
        studio_run=studio_run,
        airflow_detail=airflow_detail,
        airflow_error=airflow_error,
    )
