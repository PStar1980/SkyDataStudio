from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from skydata_studio.db.session import SessionDependency
from skydata_studio.schemas.execution import (
    PipelineRunExecutionResponse,
    PipelineRunList,
    PipelineRunRead,
    PipelineRunRequest,
    PipelineRunSummary,
)
from skydata_studio.services.pipeline_execution import (
    PipelineExecutionConflictError,
    PipelineExecutionNotFoundError,
    execute_pipeline,
    get_pipeline_run,
    list_pipeline_runs,
    pipeline_run_summary,
)

router = APIRouter()


def _database_unavailable(error: SQLAlchemyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "SkyData Studio pipeline run storage is unavailable. Start studio-postgres and run "
            "uv run python scripts/bootstrap_metadata.py."
        ),
    )


@router.get("/summary", response_model=PipelineRunSummary)
def run_summary(session: SessionDependency) -> PipelineRunSummary:
    try:
        return pipeline_run_summary(session)
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("", response_model=PipelineRunList)
def runs_list(
    session: SessionDependency,
    pipeline_id: str | None = None,
    run_status: Annotated[str | None, Query(alias="status")] = None,
    environment: str | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PipelineRunList:
    try:
        return list_pipeline_runs(
            session,
            pipeline_id=pipeline_id,
            status=run_status,
            environment=environment,
            search=search,
            limit=limit,
            offset=offset,
        )
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.get("/{run_id}", response_model=PipelineRunRead)
def run_detail(run_id: str, session: SessionDependency) -> PipelineRunRead:
    try:
        return get_pipeline_run(session, run_id)
    except PipelineExecutionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise _database_unavailable(error) from error


@router.post("", response_model=PipelineRunExecutionResponse, status_code=status.HTTP_201_CREATED)
def run_create(
    payload: PipelineRunRequest,
    session: SessionDependency,
) -> PipelineRunExecutionResponse:
    try:
        return execute_pipeline(session, payload)
    except PipelineExecutionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PipelineExecutionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _database_unavailable(error) from error
