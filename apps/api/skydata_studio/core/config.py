from functools import lru_cache

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
        default="http://localhost:5000/api", validation_alias="SKYCOMMAND_API_BASE_URL"
    )
    skycommand_api_token: str | None = Field(
        default=None, repr=False, validation_alias="SKYCOMMAND_API_TOKEN"
    )
    airflow_api_base_url: str = Field(
        default="http://localhost:8080/api/v2", validation_alias="AIRFLOW_API_BASE_URL"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
