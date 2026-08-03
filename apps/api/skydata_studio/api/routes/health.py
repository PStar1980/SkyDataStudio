from datetime import UTC, datetime

from fastapi import APIRouter

from skydata_studio.core.config import get_settings

router = APIRouter()


@router.get("")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "healthy",
        "application": "SkyData Studio API",
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
    }
