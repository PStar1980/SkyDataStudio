from fastapi import APIRouter

from skydata_studio.schemas.platform import Capability, PlatformSummary, RoadmapPhase

router = APIRouter()

CAPABILITIES = [
    Capability(
        code="CONTRACT_BRIDGE",
        name="SkyCommand Contract Bridge",
        description="Consumes trusted catalogue, freshness, quality, and ingestion-run contracts.",
        status="FOUNDATION",
        phase=2,
    ),
    Capability(
        code="METADATA_REGISTRY",
        name="Metadata Registry",
        description=(
            "Persists domains, systems, namespaces, assets, target schemas, ownership, "
            "source-to-target mappings, and lineage dependencies."
        ),
        status="FOUNDATION",
        phase=3,
    ),
    Capability(
        code="PIPELINE_WORKBENCH",
        name="ETL/ELT Pipeline Workbench",
        description=(
            "Defines versioned, parameterized, replayable post-ingestion "
            "processing pipelines."
        ),
        status="READY",
        phase=4,
    ),
    Capability(
        code="AIRFLOW",
        name="Apache Airflow Orchestration",
        description="Coordinates batch dependencies, assets, schedules, backfills, and task runs.",
        status="FOUNDATION",
        phase=5,
    ),
    Capability(
        code="DBT",
        name="dbt Transformation Layer",
        description="Builds tested staging, intermediate, mart, and semantic data models.",
        status="FOUNDATION",
        phase=6,
    ),
    Capability(
        code="QUALITY_LINEAGE",
        name="Data Quality and Reliability",
        description=(
            "Explains trust, contract gates, incidents, remediation, "
            "and reliability history."
        ),
        status="READY",
        phase=7,
    ),
    Capability(
        code="LINEAGE_IMPACT",
        name="Lineage and Impact Analysis",
        description=(
            "Stitches mappings, dbt and field dependencies, semantic delivery, "
            "quality controls, and incidents into one impact graph."
        ),
        status="FOUNDATION",
        phase=8,
    ),
    Capability(
        code="ANALYTICS_DELIVERY",
        name="Analytics Delivery",
        description="Publishes curated products to SkyWeb Analytics and Power BI.",
        status="PLANNED",
        phase=9,
    ),
]

ROADMAP = [
    RoadmapPhase(number=0, name="Repository Foundation", status="COMPLETE"),
    RoadmapPhase(number=1, name="Studio Shell and Platform Health", status="COMPLETE"),
    RoadmapPhase(number=2, name="SkyCommand Data-Contract Bridge", status="COMPLETE"),
    RoadmapPhase(number=3, name="Data Catalogue and Engineering Metadata", status="COMPLETE"),
    RoadmapPhase(number=4, name="ETL/ELT Pipeline Workbench", status="COMPLETE"),
    RoadmapPhase(number=5, name="Apache Airflow Integration", status="COMPLETE"),
    RoadmapPhase(number=6, name="dbt Transformation and Modelling", status="COMPLETE"),
    RoadmapPhase(number=7, name="Data Quality and Observability", status="COMPLETE"),
    RoadmapPhase(number=8, name="Lineage and Impact Analysis", status="IN_PROGRESS"),
    RoadmapPhase(number=9, name="Analytical Marts and Semantic Delivery", status="PLANNED"),
    RoadmapPhase(number=10, name="Power BI Integration", status="PLANNED"),
]


@router.get("/summary", response_model=PlatformSummary)
def platform_summary() -> PlatformSummary:
    return PlatformSummary(
        product="SkyData Studio",
        subtitle="Data Engineering Workbench",
        theme="Aurora Foundry",
        current_phase="Phase 8.3 — Quality and Incident Lineage Overlay Foundation",
        boundary=(
            "SkyData Studio starts after SkyCommand ingestion and publishes governed "
            "analytical products for SkyWeb Analytics, Power BI, and future consumers."
        ),
        capabilities=CAPABILITIES,
    )


@router.get("/roadmap", response_model=list[RoadmapPhase])
def roadmap() -> list[RoadmapPhase]:
    return ROADMAP
