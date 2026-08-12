from fastapi import APIRouter

from skydata_studio.api.routes import (
    airflow,
    contracts,
    dbt,
    health,
    lineage,
    metadata,
    pipeline_runs,
    pipelines,
    platform,
    quality,
    skycommand,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(
    airflow.router,
    prefix="/integrations/airflow",
    tags=["airflow-integration"],
)
api_router.include_router(platform.router, prefix="/platform", tags=["platform"])
api_router.include_router(quality.router, prefix="/quality", tags=["data-quality"])
api_router.include_router(lineage.router, prefix="/lineage", tags=["lineage-impact"])
api_router.include_router(dbt.router, prefix="/transformations/dbt", tags=["dbt-transformations"])
api_router.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["metadata-registry"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
api_router.include_router(
    pipeline_runs.router,
    prefix="/pipeline-runs",
    tags=["pipeline-runs"],
)
api_router.include_router(
    skycommand.router,
    prefix="/integrations/skycommand",
    tags=["skycommand-integration"],
)
