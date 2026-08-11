from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from skydata_studio.db.session import SessionDependency
from skydata_studio.schemas.dbt import (
    DbtModelCatalogueSummary,
    DbtSemanticLayerSummary,
    DbtTransformationSummary,
)
from skydata_studio.services.dbt_transformations import (
    dbt_model_catalogue,
    dbt_semantic_layer,
    dbt_transformation_summary,
)

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


@router.get("/models", response_model=DbtModelCatalogueSummary)
def dbt_models() -> DbtModelCatalogueSummary:
    try:
        return dbt_model_catalogue()
    except (OSError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SkyData Studio could not read the dbt runtime artifacts. "
                "Run .\\scripts\\dbt.ps1 build and refresh the model catalogue."
            ),
        ) from error


@router.get("/semantic", response_model=DbtSemanticLayerSummary)
def dbt_semantic() -> DbtSemanticLayerSummary:
    try:
        return dbt_semantic_layer()
    except (OSError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SkyData Studio could not read the dbt semantic artifacts. "
                "Run .\\scripts\\dbt.ps1 build and refresh the semantic layer."
            ),
        ) from error
