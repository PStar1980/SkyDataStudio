from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from skydata_studio.models.metadata import MetadataAsset, MetadataMapping
from skydata_studio.models.pipeline import (
    PipelineDefinition,
    PipelineRun,
    PipelineStep,
    PipelineStepRun,
    PipelineVersion,
)
from skydata_studio.schemas.execution import (
    PipelineRunExecutionResponse,
    PipelineRunList,
    PipelineRunRead,
    PipelineRunRequest,
    PipelineRunSummary,
    PipelineStepRunRead,
)


class PipelineExecutionError(RuntimeError):
    pass


class PipelineExecutionNotFoundError(PipelineExecutionError):
    pass


class PipelineExecutionConflictError(PipelineExecutionError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _pipeline_options() -> tuple[Any, ...]:
    return (
        selectinload(PipelineDefinition.versions).selectinload(PipelineVersion.parameters),
        selectinload(PipelineDefinition.versions)
        .selectinload(PipelineVersion.steps)
        .selectinload(PipelineStep.dependencies),
    )


def _run_options() -> tuple[Any, ...]:
    return (
        selectinload(PipelineRun.pipeline),
        selectinload(PipelineRun.version),
        selectinload(PipelineRun.step_runs),
    )


def _get_pipeline(session: Session, pipeline_id: str) -> PipelineDefinition:
    pipeline = session.scalar(
        select(PipelineDefinition)
        .options(*_pipeline_options())
        .where(PipelineDefinition.id == pipeline_id)
    )
    if pipeline is None:
        raise PipelineExecutionNotFoundError("Pipeline definition was not found.")
    return pipeline


def _select_version(
    pipeline: PipelineDefinition,
    version_number: int | None,
) -> PipelineVersion:
    if not pipeline.versions:
        raise PipelineExecutionConflictError("Pipeline has no executable version.")
    if version_number is None:
        version = max(pipeline.versions, key=lambda item: item.version_number)
    else:
        version = next(
            (item for item in pipeline.versions if item.version_number == version_number),
            None,
        )
        if version is None:
            raise PipelineExecutionNotFoundError(
                f"Pipeline version {version_number} was not found."
            )
    if version.status not in {"READY", "PUBLISHED"}:
        raise PipelineExecutionConflictError(
            "Only READY or PUBLISHED pipeline versions can execute locally."
        )
    return version


def _coerce_parameter(code: str, data_type: str, value: object) -> object:
    try:
        if data_type == "STRING":
            return str(value)
        if data_type == "INTEGER":
            return int(str(value))
        if data_type == "DECIMAL":
            return str(Decimal(str(value)))
        if data_type == "BOOLEAN":
            if isinstance(value, bool):
                return value
            normalized = str(value).strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
            raise ValueError("boolean value is invalid")
        if data_type == "DATE":
            if isinstance(value, datetime):
                return value.date().isoformat()
            if isinstance(value, date):
                return value.isoformat()
            return date.fromisoformat(str(value)).isoformat()
        if data_type == "TIMESTAMP":
            if isinstance(value, datetime):
                parsed = value
            else:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC).isoformat()
        if data_type == "JSON":
            return value
    except (TypeError, ValueError, InvalidOperation) as error:
        raise PipelineExecutionConflictError(
            f"Runtime parameter {code} is not a valid {data_type} value."
        ) from error
    raise PipelineExecutionConflictError(
        f"Runtime parameter {code} uses unsupported type {data_type}."
    )


def _resolve_parameters(
    version: PipelineVersion,
    supplied: dict[str, object],
) -> dict[str, object]:
    definitions = {parameter.code: parameter for parameter in version.parameters}
    normalized_supplied = {str(code).strip().upper(): value for code, value in supplied.items()}
    unknown = sorted(set(normalized_supplied) - set(definitions))
    if unknown:
        raise PipelineExecutionConflictError(
            f"Unknown runtime parameter(s): {', '.join(unknown)}."
        )

    resolved: dict[str, object] = {}
    for parameter in version.parameters:
        if parameter.code in normalized_supplied:
            raw_value = normalized_supplied[parameter.code]
        elif parameter.default_value is not None:
            raw_value = parameter.default_value
        elif parameter.code == "RUN_DATE" and parameter.data_type == "DATE":
            raw_value = _utc_now().date().isoformat()
        elif parameter.required:
            raise PipelineExecutionConflictError(
                f"Required runtime parameter {parameter.code} was not supplied."
            )
        else:
            continue
        resolved[parameter.code] = _coerce_parameter(
            parameter.code,
            parameter.data_type,
            raw_value,
        )
    return resolved


def _run_key(
    pipeline: PipelineDefinition,
    version: PipelineVersion,
    parameters: dict[str, object],
    payload: PipelineRunRequest,
) -> str:
    if payload.replay_key:
        base = payload.replay_key
    else:
        canonical = json.dumps(
            {
                "pipeline": pipeline.code,
                "version": version.version_number,
                "environment": pipeline.environment,
                "parameters": parameters,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        base = sha256(canonical.encode("utf-8")).hexdigest()[:24]
    if payload.replay_mode == "FORCE_NEW":
        return f"{base}:{uuid4().hex[:12]}"
    return base


def _get_mapping(session: Session, mapping_id: str | None) -> MetadataMapping | None:
    if mapping_id is None:
        return None
    return session.scalar(
        select(MetadataMapping)
        .options(
            selectinload(MetadataMapping.source_asset),
            selectinload(MetadataMapping.target_asset).selectinload(MetadataAsset.fields),
            selectinload(MetadataMapping.field_mappings),
        )
        .where(MetadataMapping.id == mapping_id)
    )


def _step_result(
    session: Session,
    pipeline: PipelineDefinition,
    step: PipelineStep,
    parameters: dict[str, object],
) -> dict[str, object]:
    mapping = _get_mapping(session, step.mapping_id or pipeline.mapping_id)
    source = session.get(MetadataAsset, step.source_asset_id) if step.source_asset_id else None
    target = session.get(MetadataAsset, step.target_asset_id) if step.target_asset_id else None
    common: dict[str, object] = {
        "result_version": "pipeline_step_result.v1",
        "step_code": step.code,
        "step_type": step.step_type,
        "execution_mode": "LOCAL_PROOF",
        "parameters": parameters,
        "data_mutation_applied": False,
    }

    if step.code == "READ_SOURCE":
        if source is None:
            raise PipelineExecutionConflictError("READ_SOURCE requires a registered source asset.")
        return {
            **common,
            "operation": "READ_CONTRACT_PROBE",
            "source_asset_code": source.code,
            "source_system_code": source.system.code,
            "source_namespace_code": source.namespace.code,
            "source_physical_name": source.physical_name,
            "source_contract_version": source.source_contract_version,
            "summary": (
                "Trusted source metadata resolved successfully; "
                "row materialization is deferred."
            ),
        }

    if step.step_type == "SQL" and mapping is not None:
        if mapping.status not in {"READY", "ACTIVE"}:
            raise PipelineExecutionConflictError(
                f"Mapping {mapping.code} is not READY or ACTIVE."
            )
        return {
            **common,
            "operation": "TRANSFORMATION_CONTRACT_PROBE",
            "mapping_code": mapping.code,
            "load_strategy": mapping.load_strategy,
            "field_mapping_count": len(mapping.field_mappings),
            "source_asset_code": mapping.source_asset.code,
            "target_asset_code": mapping.target_asset.code,
            "summary": (
                "Transformation contract resolved; target mutation is intentionally deferred."
            ),
        }

    if step.step_type == "VALIDATION":
        if mapping is None:
            raise PipelineExecutionConflictError("VALIDATION requires a governed mapping.")
        target_fields = list(mapping.target_asset.fields)
        if not mapping.field_mappings:
            raise PipelineExecutionConflictError(
                f"Mapping {mapping.code} has no field mappings to validate."
            )
        if not target_fields:
            raise PipelineExecutionConflictError(
                f"Target asset {mapping.target_asset.code} has no registered target schema."
            )
        target_codes = {field.code for field in target_fields}
        missing_targets = sorted(
            {
                field_mapping.target_field_code
                for field_mapping in mapping.field_mappings
                if field_mapping.target_field_code not in target_codes
            }
        )
        if missing_targets:
            raise PipelineExecutionConflictError(
                "Target schema is missing mapped field(s): " + ", ".join(missing_targets)
            )
        return {
            **common,
            "operation": "TARGET_CONTRACT_VALIDATION",
            "mapping_code": mapping.code,
            "target_asset_code": mapping.target_asset.code,
            "target_field_count": len(target_fields),
            "field_mapping_count": len(mapping.field_mappings),
            "business_keys": list(mapping.business_keys),
            "validation_status": "PASSED",
            "summary": "Target schema, field mapping, and business-key contracts are compatible.",
        }

    if step.step_type == "PUBLISH":
        if target is None and mapping is not None:
            target = mapping.target_asset
        if target is None:
            raise PipelineExecutionConflictError("PUBLISH requires a registered target asset.")
        return {
            **common,
            "operation": "PUBLICATION_ELIGIBILITY_GATE",
            "target_asset_code": target.code,
            "publication_status": "ELIGIBLE_NOT_PUBLISHED",
            "published": False,
            "summary": (
                "Dependency gates passed; physical publication is deferred "
                "to the materialization phase."
            ),
        }

    return {
        **common,
        "operation": f"{step.step_type}_CONTRACT_PROBE",
        "summary": "Step execution contract completed in local proof mode.",
    }


def _run_read(run: PipelineRun) -> PipelineRunRead:
    step_runs = list(run.step_runs)
    return PipelineRunRead(
        id=run.id,
        pipeline_id=run.pipeline_id,
        pipeline_code=run.pipeline.code,
        pipeline_name=run.pipeline.name,
        version_id=run.version_id,
        version_number=run.version.version_number,
        run_key=run.run_key,
        status=run.status,
        trigger_type=run.trigger_type,
        execution_mode=run.execution_mode,
        environment=run.environment,
        parameters=dict(run.parameters),
        execution_context=dict(run.execution_context),
        result=dict(run.result),
        replay_count=run.replay_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
        last_replayed_at=run.last_replayed_at,
        error_message=run.error_message,
        step_count=len(step_runs),
        succeeded_steps=sum(item.status == "SUCCEEDED" for item in step_runs),
        failed_steps=sum(item.status == "FAILED" for item in step_runs),
        step_runs=[
            PipelineStepRunRead(
                id=item.id,
                step_id=item.step_id,
                step_code=item.step_code,
                step_name=item.step_name,
                step_type=item.step_type,
                execution_order=item.execution_order,
                status=item.status,
                attempt_count=item.attempt_count,
                started_at=item.started_at,
                completed_at=item.completed_at,
                duration_ms=item.duration_ms,
                result=dict(item.result),
                error_message=item.error_message,
            )
            for item in step_runs
        ],
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _get_run_model(session: Session, run_id: str) -> PipelineRun:
    run = session.scalar(
        select(PipelineRun).options(*_run_options()).where(PipelineRun.id == run_id)
    )
    if run is None:
        raise PipelineExecutionNotFoundError("Pipeline run was not found.")
    return run


def execute_pipeline(
    session: Session,
    payload: PipelineRunRequest,
) -> PipelineRunExecutionResponse:
    pipeline = _get_pipeline(session, payload.pipeline_id)
    if pipeline.status not in {"READY", "ACTIVE"}:
        raise PipelineExecutionConflictError(
            "Only READY or ACTIVE pipelines can execute locally."
        )
    version = _select_version(pipeline, payload.version_number)
    parameters = _resolve_parameters(version, payload.parameters)
    run_key = _run_key(pipeline, version, parameters, payload)

    existing = session.scalar(
        select(PipelineRun)
        .options(*_run_options())
        .where(
            PipelineRun.pipeline_id == pipeline.id,
            PipelineRun.run_key == run_key,
        )
    )
    if existing is not None and payload.replay_mode == "REUSE":
        existing.replay_count += 1
        existing.last_replayed_at = _utc_now()
        session.commit()
        session.refresh(existing)
        return PipelineRunExecutionResponse(
            reused=True,
            run=_run_read(_get_run_model(session, existing.id)),
        )

    run = PipelineRun(
        pipeline=pipeline,
        version=version,
        run_key=run_key,
        status="RUNNING",
        trigger_type=payload.trigger_type,
        execution_mode="LOCAL",
        environment=pipeline.environment,
        parameters=parameters,
        execution_context={
            "engine": "SKYDATA_LOCAL_V1",
            "phase": "4.2",
            "replay_mode": payload.replay_mode,
            "structured_step_results": True,
            "data_mutation_enabled": False,
        },
        started_at=_utc_now(),
    )
    session.add(run)
    session.flush()

    step_status: dict[str, str] = {}
    blocked = False
    any_failed = False
    failure_message: str | None = None
    for step in sorted(version.steps, key=lambda item: item.execution_order):
        blocked_by = [
            dependency.depends_on_step_id
            for dependency in step.dependencies
            if step_status.get(dependency.depends_on_step_id) != "SUCCEEDED"
        ]
        step_run = PipelineStepRun(
            run=run,
            step=step,
            step_code=step.code,
            step_name=step.name,
            step_type=step.step_type,
            execution_order=step.execution_order,
        )
        session.add(step_run)
        if blocked or blocked_by:
            step_run.status = "SKIPPED"
            step_run.result = {
                "result_version": "pipeline_step_result.v1",
                "reason": "BLOCKED_BY_UPSTREAM_FAILURE",
            }
            step_status[step.id] = step_run.status
            continue

        step_run.status = "RUNNING"
        step_run.started_at = _utc_now()
        started = perf_counter()
        max_attempts = step.retry_count + 1
        for attempt in range(1, max_attempts + 1):
            step_run.attempt_count = attempt
            try:
                step_run.result = _step_result(session, pipeline, step, parameters)
                step_run.status = "SUCCEEDED"
                break
            except PipelineExecutionError as error:
                step_run.error_message = str(error)
                if attempt >= max_attempts:
                    step_run.status = "FAILED"
                    failure_message = str(error)
        step_run.completed_at = _utc_now()
        step_run.duration_ms = max(0, round((perf_counter() - started) * 1000))
        step_status[step.id] = step_run.status
        if step_run.status == "FAILED":
            any_failed = True
            if not step.continue_on_failure:
                blocked = True

    run.completed_at = _utc_now()
    run.status = "FAILED" if any_failed else "SUCCEEDED"
    run.error_message = failure_message if any_failed else None
    succeeded_steps = sum(status == "SUCCEEDED" for status in step_status.values())
    failed_steps = sum(status == "FAILED" for status in step_status.values())
    skipped_steps = sum(status == "SKIPPED" for status in step_status.values())
    run.result = {
        "result_version": "pipeline_run.v1",
        "outcome": run.status,
        "succeeded_steps": succeeded_steps,
        "failed_steps": failed_steps,
        "skipped_steps": skipped_steps,
        "total_steps": len(version.steps),
        "data_mutation_applied": False,
        "materialization_boundary": "PHASE_4_3",
    }
    session.commit()
    return PipelineRunExecutionResponse(
        reused=False,
        run=_run_read(_get_run_model(session, run.id)),
    )


def pipeline_run_summary(session: Session) -> PipelineRunSummary:
    statuses = Counter(session.scalars(select(PipelineRun.status)).all())
    environments = Counter(session.scalars(select(PipelineRun.environment)).all())
    return PipelineRunSummary(
        runs=session.scalar(select(func.count()).select_from(PipelineRun)) or 0,
        step_runs=session.scalar(select(func.count()).select_from(PipelineStepRun)) or 0,
        replayed_runs=(
            session.scalar(
                select(func.count()).select_from(PipelineRun).where(PipelineRun.replay_count > 0)
            )
            or 0
        ),
        statuses=dict(sorted(statuses.items())),
        environments=dict(sorted(environments.items())),
    )


def list_pipeline_runs(
    session: Session,
    *,
    pipeline_id: str | None = None,
    status: str | None = None,
    environment: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> PipelineRunList:
    filters: list[Any] = []
    if pipeline_id:
        filters.append(PipelineRun.pipeline_id == pipeline_id)
    if status:
        filters.append(PipelineRun.status == status.upper())
    if environment:
        filters.append(PipelineRun.environment == environment)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                PipelineRun.run_key.ilike(pattern),
                PipelineDefinition.code.ilike(pattern),
                PipelineDefinition.name.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(PipelineRun)
    query = select(PipelineRun).options(*_run_options())
    if search:
        count_query = count_query.join(
            PipelineDefinition,
            PipelineDefinition.id == PipelineRun.pipeline_id,
        )
        query = query.join(PipelineDefinition, PipelineDefinition.id == PipelineRun.pipeline_id)
    total = session.scalar(count_query.where(*filters)) or 0
    runs = session.scalars(
        query.where(*filters)
        .order_by(PipelineRun.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).unique().all()
    return PipelineRunList(total=total, items=[_run_read(run) for run in runs])


def get_pipeline_run(session: Session, run_id: str) -> PipelineRunRead:
    return _run_read(_get_run_model(session, run_id))

