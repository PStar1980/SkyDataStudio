from fastapi import APIRouter, HTTPException, status

from skydata_studio.schemas.quality import DbtQualitySummary, QualityContractSummary
from skydata_studio.services.dbt_quality import dbt_quality_summary
from skydata_studio.services.quality_contracts import quality_contract_summary

router = APIRouter()


def _artifact_unavailable(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=message,
    )


@router.get("/dbt/summary", response_model=DbtQualitySummary)
def dbt_quality() -> DbtQualitySummary:
    try:
        return dbt_quality_summary()
    except (OSError, ValueError, TypeError) as error:
        raise _artifact_unavailable(
            "SkyData Studio could not read dbt quality artifacts. "
            "Run .\\scripts\\dbt.ps1 build and refresh Data Quality."
        ) from error


@router.get("/contracts/summary", response_model=QualityContractSummary)
def quality_contract() -> QualityContractSummary:
    try:
        return quality_contract_summary()
    except (OSError, ValueError, TypeError) as error:
        raise _artifact_unavailable(
            "SkyData Studio could not evaluate the quality contract. "
            "Confirm the source-controlled contract exists, run .\\scripts\\dbt.ps1 build, "
            "and refresh Contracts."
        ) from error
