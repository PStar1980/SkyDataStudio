from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SKYDATA_",
        extra="ignore",
    )

    environment: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8100
    web_origin: str = "http://localhost:5174"
    database_url: str = Field(
        default="postgresql+psycopg://skydata:skydata@localhost:5440/skydata_studio",
        repr=False,
    )
    skycommand_api_base_url: str = Field(
        default="http://localhost:7171/api",
        validation_alias="SKYCOMMAND_API_BASE_URL",
    )
    skycommand_api_token: str | None = Field(
        default=None,
        repr=False,
        validation_alias="SKYCOMMAND_API_TOKEN",
    )
    skycommand_api_auth_mode: Literal["internal", "bearer", "none"] = Field(
        default="internal",
        validation_alias="SKYCOMMAND_API_AUTH_MODE",
    )
    skycommand_api_timeout_seconds: float = Field(
        default=8.0,
        ge=1.0,
        le=60.0,
        validation_alias="SKYCOMMAND_API_TIMEOUT_SECONDS",
    )
    skycommand_offline_preview_enabled: bool = Field(
        default=True,
        validation_alias="SKYCOMMAND_OFFLINE_PREVIEW_ENABLED",
    )
    airflow_api_base_url: str = Field(
        default="http://localhost:8080/api/v2",
        validation_alias="AIRFLOW_API_BASE_URL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
