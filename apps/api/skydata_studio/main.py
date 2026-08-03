from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from skydata_studio.api.router import api_router
from skydata_studio.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="SkyData Studio API",
    summary="Post-ingestion data engineering workbench API.",
    description=(
        "Transforms trusted SkyCommand assets into governed analytical data products "
        "through typed contracts, ETL/ELT pipelines, Airflow, dbt, quality, and lineage."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "application": "SkyData Studio",
        "subtitle": "Data Engineering Workbench",
        "api": "/api/v1",
        "documentation": "/docs",
    }
