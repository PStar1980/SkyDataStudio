from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from skydata_studio.models.metadata import MetadataMapping
from skydata_studio.models.pipeline import (
    PipelineDefinition,
    PipelineParameter,
    PipelineStep,
    PipelineStepDependency,
    PipelineVersion,
)
from skydata_studio.schemas.pipelines import (
    PipelineDefinitionCreate,
    PipelineDetail,
    PipelineList,
    PipelineListItem,
    PipelineMappingRead,
    PipelineParameterRead,
    PipelineStepDependencyRead,
    PipelineStepRead,
    PipelineSummary,
    PipelineVersionRead,
)


class PipelineRegistryError(RuntimeError):
    pass


class PipelineRegistryNotFoundError(PipelineRegistryError):
    pass


class PipelineRegistryConflictError(PipelineRegistryError):
    pass


def _mapping_options() -> tuple[Any, ...]:
    return (
        selectinload(MetadataMapping.source_asset),
        selectinload(MetadataMapping.target_asset),
    )


def _pipeline_options() -> tuple[Any, ...]:
    return (
        selectinload(PipelineDefinition.versions)
        .selectinload(PipelineVersion.parameters),
        selectinload(PipelineDefinition.versions)
        .selectinload(PipelineVersion.steps)
        .selectinload(PipelineStep.dependencies)
        .selectinload(PipelineStepDependency.depends_on_step),
    )


def _get_mapping(session: Session, mapping_id: str | None) -> MetadataMapping | None:
    if mapping_id is None:
        return None
    mapping = session.scalar(
        select(MetadataMapping).options(*_mapping_options()).where(MetadataMapping.id == mapping_id)
    )
    if mapping is None:
        raise PipelineRegistryNotFoundError("Pipeline mapping blueprint was not found.")
    return mapping


def _mapping_read(mapping: MetadataMapping | None) -> PipelineMappingRead | None:
    if mapping is None:
        return None
    return PipelineMappingRead(
        id=mapping.id,
        code=mapping.code,
        name=mapping.name,
        source_asset_code=mapping.source_asset.code,
        source_asset_name=mapping.source_asset.name,
        target_asset_code=mapping.target_asset.code,
        target_asset_name=mapping.target_asset.name,
        load_strategy=mapping.load_strategy,
        status=mapping.status,
    )


def _version_read(version: PipelineVersion) -> PipelineVersionRead:
    return PipelineVersionRead(
        id=version.id,
        version_number=version.version_number,
        status=version.status,
        notes=version.notes,
        execution_contract=dict(version.execution_contract),
        parameter_count=len(version.parameters),
        step_count=len(version.steps),
        parameters=[
            PipelineParameterRead(
                id=parameter.id,
                code=parameter.code,
                name=parameter.name,
                data_type=parameter.data_type,
                required=parameter.required,
                default_value=parameter.default_value,
                ordinal_position=parameter.ordinal_position,
                description=parameter.description,
            )
            for parameter in version.parameters
        ],
        steps=[
            PipelineStepRead(
                id=step.id,
                code=step.code,
                name=step.name,
                step_type=step.step_type,
                execution_order=step.execution_order,
                status=step.status,
                mapping_id=step.mapping_id,
                source_asset_id=step.source_asset_id,
                target_asset_id=step.target_asset_id,
                sql_text=step.sql_text,
                script_path=step.script_path,
                timeout_seconds=step.timeout_seconds,
                retry_count=step.retry_count,
                continue_on_failure=step.continue_on_failure,
                configuration=dict(step.configuration),
                dependencies=[
                    PipelineStepDependencyRead(
                        id=dependency.id,
                        depends_on_step_id=dependency.depends_on_step_id,
                        depends_on_step_code=dependency.depends_on_step.code,
                        depends_on_step_name=dependency.depends_on_step.name,
                        dependency_condition=dependency.dependency_condition,
                    )
                    for dependency in step.dependencies
                ],
            )
            for step in version.steps
        ],
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


def _pipeline_item(
    pipeline: PipelineDefinition,
    mapping: MetadataMapping | None,
) -> PipelineListItem:
    versions = list(pipeline.versions)
    current = max(versions, key=lambda item: item.version_number) if versions else None
    return PipelineListItem(
        id=pipeline.id,
        code=pipeline.code,
        name=pipeline.name,
        description=pipeline.description,
        status=pipeline.status,
        environment=pipeline.environment,
        execution_mode=pipeline.execution_mode,
        mapping=_mapping_read(mapping),
        current_version=current.version_number if current else 0,
        version_count=len(versions),
        parameter_count=len(current.parameters) if current else 0,
        step_count=len(current.steps) if current else 0,
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at,
    )


def _pipeline_detail(
    pipeline: PipelineDefinition,
    mapping: MetadataMapping | None,
) -> PipelineDetail:
    return PipelineDetail(
        **_pipeline_item(pipeline, mapping).model_dump(),
        versions=[_version_read(version) for version in pipeline.versions],
        attributes=dict(pipeline.attributes),
    )


def _get_pipeline_model(session: Session, pipeline_id: str) -> PipelineDefinition:
    pipeline = session.scalar(
        select(PipelineDefinition)
        .options(*_pipeline_options())
        .where(PipelineDefinition.id == pipeline_id)
    )
    if pipeline is None:
        raise PipelineRegistryNotFoundError("Pipeline definition was not found.")
    return pipeline


def pipeline_summary(session: Session) -> PipelineSummary:
    statuses = Counter(session.scalars(select(PipelineDefinition.status)).all())
    environments = Counter(session.scalars(select(PipelineDefinition.environment)).all())
    return PipelineSummary(
        pipelines=session.scalar(select(func.count()).select_from(PipelineDefinition)) or 0,
        versions=session.scalar(select(func.count()).select_from(PipelineVersion)) or 0,
        parameters=session.scalar(select(func.count()).select_from(PipelineParameter)) or 0,
        steps=session.scalar(select(func.count()).select_from(PipelineStep)) or 0,
        dependencies=(
            session.scalar(select(func.count()).select_from(PipelineStepDependency)) or 0
        ),
        statuses=dict(sorted(statuses.items())),
        environments=dict(sorted(environments.items())),
    )


def list_pipelines(
    session: Session,
    *,
    status: str | None = None,
    environment: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> PipelineList:
    filters: list[Any] = []
    if status:
        filters.append(PipelineDefinition.status == status.upper())
    if environment:
        filters.append(PipelineDefinition.environment == environment)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                PipelineDefinition.code.ilike(pattern),
                PipelineDefinition.name.ilike(pattern),
                PipelineDefinition.description.ilike(pattern),
            )
        )

    total = session.scalar(
        select(func.count()).select_from(PipelineDefinition).where(*filters)
    ) or 0
    pipelines = session.scalars(
        select(PipelineDefinition)
        .options(*_pipeline_options())
        .where(*filters)
        .order_by(PipelineDefinition.updated_at.desc(), PipelineDefinition.name)
        .limit(limit)
        .offset(offset)
    ).unique().all()

    mapping_ids = {pipeline.mapping_id for pipeline in pipelines if pipeline.mapping_id}
    mappings: dict[str, MetadataMapping] = {}
    if mapping_ids:
        mappings = {
            mapping.id: mapping
            for mapping in session.scalars(
                select(MetadataMapping)
                .options(*_mapping_options())
                .where(MetadataMapping.id.in_(mapping_ids))
            ).unique().all()
        }

    return PipelineList(
        total=total,
        items=[
            _pipeline_item(
                pipeline,
                mappings.get(pipeline.mapping_id) if pipeline.mapping_id else None,
            )
            for pipeline in pipelines
        ],
    )


def get_pipeline(session: Session, pipeline_id: str) -> PipelineDetail:
    pipeline = _get_pipeline_model(session, pipeline_id)
    mapping = _get_mapping(session, pipeline.mapping_id)
    return _pipeline_detail(pipeline, mapping)


def create_pipeline(
    session: Session,
    payload: PipelineDefinitionCreate,
) -> PipelineDetail:
    existing = session.scalar(
        select(PipelineDefinition).where(PipelineDefinition.code == payload.code)
    )
    if existing is not None:
        raise PipelineRegistryConflictError("This pipeline code is already registered.")

    mapping = _get_mapping(session, payload.mapping_id)
    if mapping is not None and mapping.status not in {"READY", "ACTIVE"}:
        raise PipelineRegistryConflictError(
            "A pipeline can only bind to a READY or ACTIVE mapping blueprint."
        )

    parameter_codes = [parameter.code for parameter in payload.parameters]
    if len(parameter_codes) != len(set(parameter_codes)):
        raise PipelineRegistryConflictError(
            "Pipeline parameter codes must be unique within a version."
        )

    pipeline = PipelineDefinition(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        environment=payload.environment,
        execution_mode=payload.execution_mode,
        mapping_id=payload.mapping_id,
        attributes={"registration_mode": "MANUAL", "phase": "4.1"},
    )
    version = PipelineVersion(
        version_number=1,
        status=payload.version_status,
        notes=payload.version_notes,
        execution_contract={
            "mode": "LOCAL",
            "structured_step_results": True,
            "idempotent_design_required": True,
        },
    )
    version.parameters = [
        PipelineParameter(
            code=parameter.code,
            name=parameter.name or parameter.code.replace("_", " ").title(),
            data_type=parameter.data_type,
            required=parameter.required,
            default_value=parameter.default_value,
            ordinal_position=parameter.ordinal_position,
            description=parameter.description,
        )
        for parameter in payload.parameters
    ]

    steps_by_code: dict[str, PipelineStep] = {}
    for step_input in sorted(payload.steps, key=lambda item: item.execution_order):
        step_mapping_id = step_input.mapping_id or payload.mapping_id
        source_asset_id = step_input.source_asset_id
        target_asset_id = step_input.target_asset_id
        if mapping is not None and step_mapping_id == mapping.id:
            source_asset_id = source_asset_id or mapping.source_asset_id
            target_asset_id = target_asset_id or mapping.target_asset_id
        step = PipelineStep(
            code=step_input.code,
            name=step_input.name,
            step_type=step_input.step_type,
            execution_order=step_input.execution_order,
            status=step_input.status,
            mapping_id=step_mapping_id,
            source_asset_id=source_asset_id,
            target_asset_id=target_asset_id,
            sql_text=step_input.sql_text,
            script_path=step_input.script_path,
            timeout_seconds=step_input.timeout_seconds,
            retry_count=step_input.retry_count,
            continue_on_failure=step_input.continue_on_failure,
            configuration=dict(step_input.configuration),
        )
        version.steps.append(step)
        steps_by_code[step_input.code] = step

    pipeline.versions.append(version)
    session.add(pipeline)
    session.flush()

    for step_input in payload.steps:
        step = steps_by_code[step_input.code]
        for dependency_code in step_input.depends_on_codes:
            session.add(
                PipelineStepDependency(
                    step=step,
                    depends_on_step=steps_by_code[dependency_code],
                    dependency_condition="SUCCESS",
                )
            )

    session.commit()
    return get_pipeline(session, pipeline.id)
