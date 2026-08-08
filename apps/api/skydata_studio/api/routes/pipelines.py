from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from skydata_studio.db.session import SessionDependency
from skydata_studio.schemas.pipelines import (
    PipelineDefinitionCreate,
    PipelineDetail,
    PipelineList,
    PipelineSummary,
)
from skydata_studio.services.pipeline_registry import (
    PipelineRegistryConflictError,
    PipelineRegistryNotFoundError,
    create_pipeline,
    get_pipeline,
    list_pipelines,
    pipeline_summary,
)

router = APIRouter()


def _database_unavailable(error: SQLAlchemyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "SkyData Studio pipeline storage is unavailable. Start studio-postgres and run "
            "uv run python scripts/bootstrap_metadata.py."
        ),
    )


@router.get("/summary", response_model=PipelineSummary)
def pipelines_summary(session: SessionDependency) -> PipelineSummary:
    try:
        return pipeline_summary(session)
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("", response_model=PipelineList)
def pipelines_list(
    session: SessionDependency,
    pipeline_status: Annotated[str | None, Query(alias="status")] = None,
    environment: str | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PipelineList:
    try:
        return list_pipelines(
            session,
            status=pipeline_status,
            environment=environment,
            search=search,
            limit=limit,
            offset=offset,
        )
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/{pipeline_id}", response_model=PipelineDetail)
def pipeline_detail(pipeline_id: str, session: SessionDependency) -> PipelineDetail:
    try:
        return get_pipeline(session, pipeline_id)
    except PipelineRegistryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.post("", response_model=PipelineDetail, status_code=status.HTTP_201_CREATED)
def pipeline_create(
    payload: PipelineDefinitionCreate,
    session: SessionDependency,
) -> PipelineDetail:
    try:
        return create_pipeline(session, payload)
    except PipelineRegistryNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PipelineRegistryConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _database_unavailable(error) from error
