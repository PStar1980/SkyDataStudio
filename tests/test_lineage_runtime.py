from datetime import UTC, datetime

from skydata_studio.schemas.airflow import (
    AirflowDagRunDetail,
    AirflowDagRunSummary,
    AirflowTaskInstanceSummary,
)
from skydata_studio.schemas.execution import PipelineRunRead, PipelineStepRunRead
from skydata_studio.schemas.lineage import (
    LineageEdge,
    LineageImpactSummary,
    LineageNode,
    LineageSummary,
)
from skydata_studio.services.lineage_runtime import compose_runtime_lineage_summary

NOW = datetime(2026, 8, 13, 1, 0, tzinfo=UTC)
DAG_RUN_ID = "skydata__proof_runtime"


def _asset_lineage() -> LineageSummary:
    source = LineageNode(
        id="metadata:source",
        label="DFF",
        node_type="SOURCE_ASSET",
        layer="RAW",
        system="SKYCOMMAND",
        relation="DFF",
        status="READY",
    )
    target = LineageNode(
        id="metadata:target",
        label="FED_FUNDS_RATE_MART",
        node_type="CURATED_ASSET",
        layer="MART",
        system="SKYDATA",
        relation="FED_FUNDS_RATE_MART",
        status="READY",
    )
    return LineageSummary(
        artifact_status="READY",
        metadata_mapping_count=1,
        dbt_model_count=0,
        semantic_model_count=0,
        metric_count=0,
        node_count=2,
        edge_count=1,
        nodes=[source, target],
        edges=[
            LineageEdge(
                id="mapping:proof",
                upstream_id=source.id,
                downstream_id=target.id,
                edge_type="MAPPING",
                label="TRANSFORM",
            )
        ],
        default_impact=LineageImpactSummary(
            selected_node_id=source.id,
            selected_node_label=source.label,
            downstream_node_count=1,
            affected_model_count=0,
            affected_semantic_model_count=0,
            affected_metric_count=0,
            affected_layers=["MART"],
            nodes=[target],
        ),
    )


def _studio_run() -> PipelineRunRead:
    step_codes = [
        ("READ_SOURCE", "SQL"),
        ("TRANSFORM_MART", "SQL"),
        ("VALIDATE_TARGET", "VALIDATION"),
        ("PUBLISH_TARGET", "PUBLISH"),
    ]
    steps = [
        PipelineStepRunRead(
            id=f"step-{index}",
            step_id=f"definition-step-{index}",
            step_code=code,
            step_name=code.replace("_", " ").title(),
            step_type=step_type,
            execution_order=index,
            status="SUCCEEDED",
            attempt_count=1,
            started_at=NOW,
            completed_at=NOW,
            duration_ms=10,
            result={"operation": code},
            error_message=None,
        )
        for index, (code, step_type) in enumerate(step_codes, start=1)
    ]
    return PipelineRunRead(
        id="studio-run-1",
        pipeline_id="pipeline-1",
        pipeline_code="FED_FUNDS_RATE_PIPELINE",
        pipeline_name="Federal Funds Rate Pipeline",
        version_id="version-1",
        version_number=1,
        run_key=f"AIRFLOW:{DAG_RUN_ID}",
        status="SUCCEEDED",
        trigger_type="AIRFLOW",
        execution_mode="LOCAL",
        environment="development",
        parameters={"RUN_DATE": "2026-08-12"},
        execution_context={},
        result={
            "materialization_executed": True,
            "data_mutation_applied": False,
            "target_relation": "mart.fed_funds_rate",
            "target_row_count": 26335,
        },
        replay_count=1,
        started_at=NOW,
        completed_at=NOW,
        last_replayed_at=NOW,
        error_message=None,
        step_count=4,
        succeeded_steps=4,
        failed_steps=0,
        step_runs=steps,
        created_at=NOW,
        updated_at=NOW,
    )


def _airflow_detail() -> AirflowDagRunDetail:
    task_ids = [
        "resolve_pipeline_contract",
        "execute_studio_pipeline",
        "validate_materialization",
        "publish_batch_evidence",
    ]
    tasks = [
        AirflowTaskInstanceSummary(
            task_id=task_id,
            task_display_name=task_id.replace("_", " ").title(),
            state="success",
            try_number=1,
            start_date=NOW,
            end_date=NOW,
            duration=0.1,
            operator="PythonOperator",
        )
        for task_id in task_ids
    ]
    return AirflowDagRunDetail(
        run=AirflowDagRunSummary(
            dag_id="skydata_studio_fed_funds_rate_pipeline",
            dag_run_id=DAG_RUN_ID,
            state="success",
            run_type="manual",
            logical_date=NOW,
            start_date=NOW,
            end_date=NOW,
            conf={"pipeline_code": "FED_FUNDS_RATE_PIPELINE"},
        ),
        tasks=tasks,
        task_state_counts={"success": 4},
        studio_run_key=f"AIRFLOW:{DAG_RUN_ID}",
    )


def test_runtime_lineage_composes_airflow_and_studio_execution_proof() -> None:
    summary = compose_runtime_lineage_summary(
        asset_lineage=_asset_lineage(),
        studio_run=_studio_run(),
        airflow_detail=_airflow_detail(),
    )

    assert summary.runtime_status == "READY"
    assert summary.airflow_connection_status == "CONNECTED"
    assert summary.airflow_task_count == 4
    assert summary.successful_airflow_task_count == 4
    assert summary.studio_step_count == 4
    assert summary.succeeded_studio_step_count == 4
    assert summary.node_count == 14
    assert summary.edge_count == 13


def test_runtime_lineage_links_airflow_callback_to_replay_safe_studio_run() -> None:
    summary = compose_runtime_lineage_summary(
        asset_lineage=_asset_lineage(),
        studio_run=_studio_run(),
        airflow_detail=_airflow_detail(),
    )

    assert summary.dag_run_id == DAG_RUN_ID
    assert summary.studio_run_key == f"AIRFLOW:{DAG_RUN_ID}"
    assert summary.replay_count == 1
    callback_edges = [edge for edge in summary.edges if edge.edge_type == "CALLS_STUDIO"]
    assert len(callback_edges) == 1
    assert "execute_studio_pipeline" in callback_edges[0].upstream_id
    assert callback_edges[0].downstream_id == "studio-run:studio-run-1"


def test_runtime_lineage_links_publish_step_to_structural_target() -> None:
    summary = compose_runtime_lineage_summary(
        asset_lineage=_asset_lineage(),
        studio_run=_studio_run(),
        airflow_detail=_airflow_detail(),
    )

    materialization = next(edge for edge in summary.edges if edge.edge_type == "MATERIALIZES")
    assert materialization.upstream_id == "studio-step:step-4"
    assert materialization.downstream_id == "metadata:target"
    assert summary.materialization_executed is True
    assert summary.data_mutation_applied is False
    assert summary.target_relation == "mart.fed_funds_rate"
    assert summary.target_row_count == 26335


def test_runtime_lineage_degrades_when_airflow_is_unavailable() -> None:
    summary = compose_runtime_lineage_summary(
        asset_lineage=_asset_lineage(),
        studio_run=_studio_run(),
        airflow_detail=None,
        airflow_error="Airflow API is unavailable.",
    )

    assert summary.runtime_status == "PARTIAL"
    assert summary.airflow_connection_status == "UNAVAILABLE"
    assert summary.airflow_task_count == 0
    assert summary.studio_step_count == 4
    assert summary.airflow_error == "Airflow API is unavailable."
    assert any(edge.edge_type == "CALLS_STUDIO" for edge in summary.edges)
