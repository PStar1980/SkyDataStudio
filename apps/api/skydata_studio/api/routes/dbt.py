from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from skydata_studio.db.session import SessionDependency
from skydata_studio.schemas.dbt import DbtTransformationSummary
from skydata_studio.services.dbt_transformations import dbt_transformation_summary

router = APIRouter()


@router.get("/summary", response_model=DbtTransformationSummary)
def dbt_summary(session: SessionDependency) -> DbtTransformationSummary:
    try:
        return dbt_transformation_summary(session)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SkyData Studio transformation storage is unavailable. Start studio-postgres "
                "and run uv run python scripts/bootstrap_metadata.py."
            ),
        ) from error
