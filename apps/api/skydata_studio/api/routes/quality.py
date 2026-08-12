from fastapi import APIRouter, HTTPException, status

from skydata_studio.schemas.quality import DbtQualitySummary
from skydata_studio.services.dbt_quality import dbt_quality_summary

router = APIRouter()


@router.get("/dbt/summary", response_model=DbtQualitySummary)
def dbt_quality() -> DbtQualitySummary:
    try:
        return dbt_quality_summary()
    except (OSError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SkyData Studio could not read dbt quality artifacts. "
                "Run .\\scripts\\dbt.ps1 build and refresh Data Quality."
            ),
        ) from error
