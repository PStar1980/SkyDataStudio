from sqlalchemy import Engine

from skydata_studio.db.base import Base
from skydata_studio.db.session import get_engine
from skydata_studio.models import metadata as _metadata_models  # noqa: F401
from skydata_studio.models import pipeline as _pipeline_models  # noqa: F401
from skydata_studio.models import quality as _quality_models  # noqa: F401


def create_metadata_schema(engine: Engine | None = None) -> None:
    Base.metadata.create_all(bind=engine or get_engine())
