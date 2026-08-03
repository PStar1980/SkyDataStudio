"""Initial Airflow 3 Task SDK proof for SkyData Studio.

This DAG is intentionally dependency-light. It proves the public authoring seam and will
be replaced by the first SkyCommand-to-Studio asset pipeline in Phase 5.
"""

from datetime import UTC, datetime

from airflow.sdk import dag, task


@dag(
    dag_id="skydata_studio_platform_smoke",
    description="Validate the SkyData Studio Airflow authoring seam.",
    schedule=None,
    start_date=datetime(2026, 8, 3, tzinfo=UTC),
    catchup=False,
    tags=["skydata-studio", "foundation"],
)
def studio_platform_smoke():
    @task
    def platform_identity() -> dict[str, str]:
        return {
            "product": "SkyData Studio",
            "responsibility": "post-ingestion data engineering",
            "status": "scaffolded",
        }

    @task
    def validate_boundary(identity: dict[str, str]) -> str:
        assert identity["responsibility"] == "post-ingestion data engineering"
        return "SkyData Studio Airflow boundary validated."

    validate_boundary(platform_identity())


studio_platform_smoke()
