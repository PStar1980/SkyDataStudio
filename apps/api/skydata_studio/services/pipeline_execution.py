from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    and_,
    func,
    insert,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.orm import Session, selectinload

from skydata_studio.integrations.skycommand.client import SkyCommandClientError
from skydata_studio.integrations.skycommand.dependencies import SkyCommandGateway
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


EXECUTION_ENGINE_VERSION = "SKYDATA_LOCAL_V2"
MATERIALIZATION_PHASE = "4.3"
OBSERVATION_PAGE_SIZE = 5000
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NUMERIC_PATTERN = re.compile(r"^NUMERIC(?:\((\d+)(?:,(\d+))?\))?$", re.IGNORECASE)
_VARCHAR_PATTERN = re.compile(r"^(?:VAR)?CHAR(?:\((\d+)\))?$", re.IGNORECASE)


@dataclass
class _ExecutionState:
    source_rows: list[dict[str, object]] = field(default_factory=list)
    transformed_rows: list[dict[str, object]] = field(default_factory=list)
    rejected_rows: int = 0
    source_contract_version: str | None = None
    source_pages: int = 0
    source_first_date: str | None = None
    source_latest_date: str | None = None


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
        selectinload(PipelineDefinition.versions).selectinload(
            PipelineVersion.parameters
        ),
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
        version = max(
            pipeline.versions,
            key=lambda item: item.version_number,
        )
    else:
        matched_version = next(
            (
                item
                for item in pipeline.versions
                if item.version_number == version_number
            ),
            None,
        )
        if matched_version is None:
            raise PipelineExecutionNotFoundError(
                f"Pipeline version {version_number} was not found."
            )
        version = matched_version

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
    normalized_supplied = {
        str(code).strip().upper(): value for code, value in supplied.items()
    }
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
                "engine": EXECUTION_ENGINE_VERSION,
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
            selectinload(MetadataMapping.target_asset).selectinload(
                MetadataAsset.fields
            ),
            selectinload(MetadataMapping.field_mappings),
        )
        .where(MetadataMapping.id == mapping_id)
    )


def _safe_identifier(value: str | None, *, fallback: str, label: str) -> str:
    identifier = (value or fallback).strip()
    if not _IDENTIFIER_PATTERN.fullmatch(identifier):
        raise PipelineExecutionConflictError(
            f"{label} {identifier!r} is not a safe SQL identifier."
        )
    return identifier.lower()


def _sqlalchemy_type(data_type: str) -> Any:
    normalized = data_type.strip().upper()
    numeric = _NUMERIC_PATTERN.fullmatch(normalized)
    if numeric:
        precision = int(numeric.group(1)) if numeric.group(1) else 38
        scale = int(numeric.group(2)) if numeric.group(2) else 0
        return Numeric(precision=precision, scale=scale)
    varchar = _VARCHAR_PATTERN.fullmatch(normalized)
    if varchar:
        length = int(varchar.group(1)) if varchar.group(1) else 255
        return String(length)
    if normalized == "DATE":
        return Date()
    if normalized in {"TIMESTAMP", "DATETIME"}:
        return DateTime(timezone=True)
    if normalized in {"INTEGER", "INT"}:
        return Integer()
    if normalized in {"BIGINT", "LONG"}:
        return BigInteger()
    if normalized in {"BOOLEAN", "BOOL"}:
        return Boolean()
    if normalized in {"TEXT", "STRING"}:
        return Text()
    raise PipelineExecutionConflictError(
        f"Target data type {data_type!r} is not supported by the local materializer."
    )


def _coerce_target_value(value: object, data_type: str) -> object:
    if value is None:
        return None
    normalized = data_type.strip().upper()
    try:
        if normalized == "DATE":
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return date.fromisoformat(str(value))
        if normalized in {"TIMESTAMP", "DATETIME"}:
            if isinstance(value, datetime):
                parsed = value
            else:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        if _NUMERIC_PATTERN.fullmatch(normalized):
            return Decimal(str(value))
        if normalized in {"INTEGER", "INT", "BIGINT", "LONG"}:
            return int(str(value))
        if normalized in {"BOOLEAN", "BOOL"}:
            if isinstance(value, bool):
                return value
            text_value = str(value).strip().lower()
            if text_value in {"true", "1", "yes", "y"}:
                return True
            if text_value in {"false", "0", "no", "n"}:
                return False
            raise ValueError("invalid boolean")
        if normalized in {"TEXT", "STRING"} or _VARCHAR_PATTERN.fullmatch(normalized):
            return str(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise PipelineExecutionConflictError(
            f"Value {value!r} cannot be coerced to target type {data_type}."
        ) from error
    raise PipelineExecutionConflictError(
        f"Target data type {data_type!r} is not supported by the local transformer."
    )


async def _read_source_rows(
    gateway: SkyCommandGateway,
    source: MetadataAsset,
    parameters: dict[str, object],
    state: _ExecutionState,
) -> None:
    domain_code = source.domain.code
    asset_code = source.source_asset_code or source.code
    run_date = parameters.get("RUN_DATE")
    date_to = str(run_date) if run_date is not None else None
    offset = 0
    rows: list[dict[str, object]] = []
    pages = 0
    expected_total: int | None = None
    contract_version: str | None = None

    try:
        while expected_total is None or offset < expected_total:
            payload = await gateway.list_asset_observations(
                domain_code=domain_code,
                asset_code=asset_code,
                date_to=date_to,
                limit=OBSERVATION_PAGE_SIZE,
                offset=offset,
                sort_direction="ASC",
            )
            if payload.asset.asset_code.upper() != asset_code.upper():
                raise PipelineExecutionConflictError(
                    "SkyCommand observation payload returned the wrong source asset."
                )
            contract_version = payload.contract_version
            expected_total = payload.total
            pages += 1
            batch = [
                {
                    "OBSERVATION_DATE": item.observation_date.isoformat(),
                    "VALUE": item.value,
                }
                for item in payload.items
            ]
            rows.extend(batch)
            if not batch:
                break
            offset += len(batch)
            if pages > 10000:
                raise PipelineExecutionConflictError(
                    "SkyCommand observation pagination exceeded the safety limit."
                )
    except SkyCommandClientError as error:
        raise PipelineExecutionConflictError(
            f"SkyCommand source observations could not be read: {error}"
        ) from error

    if not rows:
        raise PipelineExecutionConflictError(
            f"SkyCommand returned no observations for {domain_code}/{asset_code}."
        )

    state.source_rows = rows
    state.source_contract_version = contract_version
    state.source_pages = pages
    state.source_first_date = str(rows[0]["OBSERVATION_DATE"])
    state.source_latest_date = str(rows[-1]["OBSERVATION_DATE"])


def _transform_rows(mapping: MetadataMapping, state: _ExecutionState) -> None:
    transformed: list[dict[str, object]] = []
    rejected = 0
    field_mappings = list(mapping.field_mappings)
    if not field_mappings:
        raise PipelineExecutionConflictError(
            f"Mapping {mapping.code} has no field mappings to execute."
        )

    for source_row in state.source_rows:
        target_row: dict[str, object] = {}
        try:
            for field_mapping in field_mappings:
                source_code = field_mapping.source_field_code
                if not source_code:
                    raise PipelineExecutionConflictError(
                        f"Field mapping {field_mapping.target_field_code} has no source field."
                    )
                source_key = source_code.upper()
                if source_key not in source_row:
                    raise PipelineExecutionConflictError(
                        f"Source field {source_code} is missing from the governed payload."
                    )
                raw_value = source_row[source_key]
                if raw_value is None and not field_mapping.nullable:
                    raise PipelineExecutionConflictError(
                        f"Required source field {source_code} is null."
                    )
                transformation_type = (
                    field_mapping.transformation_type or "DIRECT"
                ).upper()
                if transformation_type not in {"DIRECT", "CAST"}:
                    raise PipelineExecutionConflictError(
                        "Phase 4.3 supports DIRECT and CAST field transformations only; "
                        f"received {transformation_type}."
                    )
                target_row[field_mapping.target_field_code.lower()] = _coerce_target_value(
                    raw_value,
                    field_mapping.target_data_type,
                )
        except PipelineExecutionConflictError:
            rejected += 1
            continue
        transformed.append(target_row)

    state.transformed_rows = transformed
    state.rejected_rows = rejected


def _validate_transformed_rows(mapping: MetadataMapping, state: _ExecutionState) -> None:
    if not state.transformed_rows:
        raise PipelineExecutionConflictError("Transformation produced no publishable rows.")
    if state.rejected_rows:
        raise PipelineExecutionConflictError(
            f"Transformation rejected {state.rejected_rows} row(s); publication is blocked."
        )

    target_fields = {field.code.upper(): field for field in mapping.target_asset.fields}
    mapped_targets = {item.target_field_code.upper() for item in mapping.field_mappings}
    missing_targets = sorted(mapped_targets - set(target_fields))
    if missing_targets:
        raise PipelineExecutionConflictError(
            "Target schema is missing mapped field(s): " + ", ".join(missing_targets)
        )

    business_keys = [code.upper() for code in mapping.business_keys]
    if not business_keys:
        business_keys = [
            item.target_field_code.upper()
            for item in mapping.field_mappings
            if item.key_field
        ]
    if not business_keys:
        raise PipelineExecutionConflictError(
            f"Mapping {mapping.code} requires at least one business key for MERGE execution."
        )

    seen: set[tuple[object, ...]] = set()
    for row in state.transformed_rows:
        key = tuple(row.get(code.lower()) for code in business_keys)
        if any(value is None for value in key):
            raise PipelineExecutionConflictError(
                "A transformed row is missing a required MERGE business key."
            )
        if key in seen:
            raise PipelineExecutionConflictError(
                f"Transformation produced duplicate business key {key!r}."
            )
        seen.add(key)


def _target_table(session: Session, mapping: MetadataMapping) -> tuple[Table, str | None, str]:
    target = mapping.target_asset
    connection = session.connection()
    dialect = connection.dialect.name
    schema = None
    if dialect != "sqlite":
        schema = _safe_identifier(
            target.namespace.physical_name,
            fallback=target.namespace.code,
            label="Target schema",
        )
        session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    table_name = _safe_identifier(
        target.physical_name,
        fallback=target.code,
        label="Target table",
    )

    metadata = MetaData()
    columns = []
    for asset_field in target.fields:
        columns.append(
            Column(
                _safe_identifier(
                    asset_field.code,
                    fallback=asset_field.code,
                    label="Target field",
                ),
                _sqlalchemy_type(asset_field.data_type),
                primary_key=asset_field.key_field,
                nullable=asset_field.nullable and not asset_field.key_field,
            )
        )
    if not columns:
        raise PipelineExecutionConflictError(
            f"Target asset {target.code} has no physical schema to materialize."
        )
    table = Table(table_name, metadata, *columns, schema=schema)
    table.create(connection, checkfirst=True)
    relation = f"{schema}.{table_name}" if schema else table_name
    return table, schema, relation


def _materialize_rows(
    session: Session,
    mapping: MetadataMapping,
    state: _ExecutionState,
) -> dict[str, object]:
    if mapping.load_strategy != "MERGE":
        raise PipelineExecutionConflictError(
            f"Phase 4.3 local materialization supports MERGE, not {mapping.load_strategy}."
        )
    _validate_transformed_rows(mapping, state)
    table, _, relation = _target_table(session, mapping)
    key_codes = [code.lower() for code in mapping.business_keys]
    if not key_codes:
        key_codes = [
            item.target_field_code.lower()
            for item in mapping.field_mappings
            if item.key_field
        ]
    value_codes = [column.name for column in table.columns if column.name not in key_codes]

    existing = session.execute(select(table)).mappings().all()
    existing_by_key = {
        tuple(row[code] for code in key_codes): row
        for row in existing
    }
    inserts: list[dict[str, object]] = []
    updates: list[tuple[tuple[object, ...], dict[str, object]]] = []
    unchanged = 0
    for row in state.transformed_rows:
        key = tuple(row[code] for code in key_codes)
        prior = existing_by_key.get(key)
        if prior is None:
            inserts.append(row)
            continue
        changed_values = {
            code: row[code]
            for code in value_codes
            if prior[code] != row[code]
        }
        if changed_values:
            updates.append((key, changed_values))
        else:
            unchanged += 1

    with session.begin_nested():
        if inserts:
            session.execute(insert(table), inserts)
        for key, values in updates:
            predicates = [
                table.c[code] == value
                for code, value in zip(key_codes, key, strict=True)
            ]
            session.execute(update(table).where(and_(*predicates)).values(**values))

    target_row_count = session.scalar(select(func.count()).select_from(table)) or 0
    return {
        "target_relation": relation,
        "rows_read": len(state.source_rows),
        "rows_transformed": len(state.transformed_rows),
        "rows_inserted": len(inserts),
        "rows_updated": len(updates),
        "rows_changed": len(inserts) + len(updates),
        "rows_unchanged": unchanged,
        "rows_rejected": state.rejected_rows,
        "rows_published": len(state.transformed_rows),
        "target_row_count": int(target_row_count),
    }


async def _step_result(
    session: Session,
    pipeline: PipelineDefinition,
    step: PipelineStep,
    parameters: dict[str, object],
    gateway: SkyCommandGateway,
    state: _ExecutionState,
) -> dict[str, object]:
    mapping = _get_mapping(session, step.mapping_id or pipeline.mapping_id)
    source = (
        session.get(MetadataAsset, step.source_asset_id)
        if step.source_asset_id
        else None
    )
    target = (
        session.get(MetadataAsset, step.target_asset_id)
        if step.target_asset_id
        else None
    )
    common: dict[str, object] = {
        "result_version": "pipeline_step_result.v1",
        "step_code": step.code,
        "step_type": step.step_type,
        "execution_mode": "LOCAL_MATERIALIZE",
        "parameters": parameters,
        "data_mutation_applied": False,
    }

    if step.code == "READ_SOURCE":
        if source is None:
            raise PipelineExecutionConflictError(
                "READ_SOURCE requires a registered source asset."
            )
        await _read_source_rows(gateway, source, parameters, state)
        return {
            **common,
            "operation": "READ_GOVERNED_OBSERVATIONS",
            "source_asset_code": source.code,
            "source_system_code": source.system.code,
            "source_namespace_code": source.namespace.code,
            "source_physical_name": source.physical_name,
            "source_contract_version": state.source_contract_version,
            "rows_read": len(state.source_rows),
            "pages_read": state.source_pages,
            "source_first_date": state.source_first_date,
            "source_latest_date": state.source_latest_date,
            "summary": (
                "Trusted observations were read through SkyCommand's portable data contract."
            ),
        }

    if step.step_type == "SQL" and mapping is not None:
        if mapping.status not in {"READY", "ACTIVE"}:
            raise PipelineExecutionConflictError(
                f"Mapping {mapping.code} is not READY or ACTIVE."
            )
        _transform_rows(mapping, state)
        return {
            **common,
            "operation": "TRANSFORM_SOURCE_TO_TARGET",
            "mapping_code": mapping.code,
            "load_strategy": mapping.load_strategy,
            "field_mapping_count": len(mapping.field_mappings),
            "source_asset_code": mapping.source_asset.code,
            "target_asset_code": mapping.target_asset.code,
            "rows_read": len(state.source_rows),
            "rows_transformed": len(state.transformed_rows),
            "rows_rejected": state.rejected_rows,
            "summary": "The governed field mapping produced an in-memory curated row set.",
        }

    if step.step_type == "VALIDATION":
        if mapping is None:
            raise PipelineExecutionConflictError(
                "VALIDATION requires a governed mapping."
            )
        _validate_transformed_rows(mapping, state)
        target_fields = list(mapping.target_asset.fields)
        return {
            **common,
            "operation": "MATERIALIZATION_PRECHECK",
            "mapping_code": mapping.code,
            "target_asset_code": mapping.target_asset.code,
            "target_field_count": len(target_fields),
            "field_mapping_count": len(mapping.field_mappings),
            "business_keys": list(mapping.business_keys),
            "rows_validated": len(state.transformed_rows),
            "rows_rejected": state.rejected_rows,
            "validation_status": "PASSED",
            "summary": (
                "Target schema, business keys, and transformed rows passed publication checks."
            ),
        }

    if step.step_type == "PUBLISH":
        if target is None and mapping is not None:
            target = mapping.target_asset
        if target is None:
            raise PipelineExecutionConflictError(
                "PUBLISH requires a registered target asset."
            )
        if mapping is None:
            raise PipelineExecutionConflictError(
                "PUBLISH requires a governed source-to-target mapping."
            )
        materialization = _materialize_rows(session, mapping, state)
        return {
            **common,
            **materialization,
            "operation": "MERGE_AND_PUBLISH_TARGET",
            "target_asset_code": target.code,
            "publication_status": "PUBLISHED",
            "published": True,
            "materialization_executed": True,
            "data_mutation_applied": bool(materialization["rows_changed"]),
            "summary": (
                "Dependency gates passed and the curated target was materialized idempotently."
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


async def execute_pipeline(
    session: Session,
    payload: PipelineRunRequest,
    gateway: SkyCommandGateway,
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
            "engine": EXECUTION_ENGINE_VERSION,
            "phase": MATERIALIZATION_PHASE,
            "replay_mode": payload.replay_mode,
            "structured_step_results": True,
            "data_mutation_enabled": True,
            "source_contract": "time_series_observations.v1",
            "materialization_strategy": "MERGE",
        },
        started_at=_utc_now(),
    )
    session.add(run)
    session.flush()

    step_status: dict[str, str] = {}
    blocked = False
    any_failed = False
    failure_message: str | None = None
    state = _ExecutionState()
    materialization_result: dict[str, object] = {}
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
                step_run.result = await _step_result(
                    session,
                    pipeline,
                    step,
                    parameters,
                    gateway,
                    state,
                )
                if step_run.result.get("materialization_executed") is True:
                    materialization_result = dict(step_run.result)
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
        "materialization_executed": materialization_result.get(
            "materialization_executed"
        )
        is True,
        "data_mutation_applied": materialization_result.get("data_mutation_applied")
        is True,
        "materialization_boundary": "PHASE_4_3",
        "target_relation": materialization_result.get("target_relation"),
        "rows_read": materialization_result.get("rows_read", len(state.source_rows)),
        "rows_transformed": materialization_result.get(
            "rows_transformed", len(state.transformed_rows)
        ),
        "rows_inserted": materialization_result.get("rows_inserted", 0),
        "rows_updated": materialization_result.get("rows_updated", 0),
        "rows_changed": materialization_result.get("rows_changed", 0),
        "rows_unchanged": materialization_result.get("rows_unchanged", 0),
        "rows_rejected": materialization_result.get("rows_rejected", state.rejected_rows),
        "rows_published": materialization_result.get("rows_published", 0),
        "target_row_count": materialization_result.get("target_row_count"),
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
        step_runs=session.scalar(select(func.count()).select_from(PipelineStepRun))
        or 0,
        replayed_runs=(
            session.scalar(
                select(func.count())
                .select_from(PipelineRun)
                .where(PipelineRun.replay_count > 0)
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
        query = query.join(
            PipelineDefinition, PipelineDefinition.id == PipelineRun.pipeline_id
        )
    total = session.scalar(count_query.where(*filters)) or 0
    runs = (
        session.scalars(
            query.where(*filters)
            .order_by(PipelineRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .all()
    )
    return PipelineRunList(total=total, items=[_run_read(run) for run in runs])


def get_pipeline_run(session: Session, run_id: str) -> PipelineRunRead:
    return _run_read(_get_run_model(session, run_id))
