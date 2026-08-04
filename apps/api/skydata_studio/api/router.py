from fastapi import APIRouter

from skydata_studio.api.routes import contracts, health, platform, skycommand

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(platform.router, prefix="/platform", tags=["platform"])
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
api_router.include_router(
    skycommand.router,
    prefix="/integrations/skycommand",
    tags=["skycommand-integration"],
)
