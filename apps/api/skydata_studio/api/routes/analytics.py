from fastapi import APIRouter, HTTPException, status

from skydata_studio.db.session import SessionDependency
from skydata_studio.schemas.analytics import AnalyticsProductSummary
from skydata_studio.services.analytics_products import analytics_product_summary

router = APIRouter()


@router.get("/products/summary", response_model=AnalyticsProductSummary)
def product_summary(session: SessionDependency) -> AnalyticsProductSummary:
    try:
        return analytics_product_summary(session)
    except (OSError, ValueError, TypeError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SkyData Studio could not compose analytical-product readiness. "
                "Verify product contracts, dbt artifacts, and Studio PostgreSQL."
            ),
        ) from error
