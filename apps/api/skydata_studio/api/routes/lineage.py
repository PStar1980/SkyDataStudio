from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from skydata_studio.core.config import Settings, get_settings
from skydata_studio.db.session import SessionDependency
from skydata_studio.schemas.lineage import (
    FieldLineageImpactSummary,
    FieldLineageSummary,
    LineageImpactSummary,
    LineageSummary,
    LineageTrustSummary,
    RuntimeLineageSummary,
)
from skydata_studio.services.lineage import (
    field_lineage_impact,
    field_lineage_summary,
    lineage_impact,
    lineage_summary,
)
from skydata_studio.services.lineage_runtime import runtime_lineage_summary
from skydata_studio.services.lineage_trust import lineage_trust_summary

router = APIRouter()


def _unavailable(_error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "SkyData Studio could not compose cross-layer lineage. Ensure Studio PostgreSQL "
            "is available and run .\\scripts\\dbt.ps1 build so dbt artifacts are current."
        ),
    )


@router.get("/summary", response_model=LineageSummary)
def lineage_graph(
    session: SessionDependency,
    focus_node_id: Annotated[str | None, Query(alias="focusNodeId")] = None,
) -> LineageSummary:
    try:
        return lineage_summary(session, focus_node_id=focus_node_id)
    except (SQLAlchemyError, OSError, ValueError, TypeError) as error:
        raise _unavailable(error) from error


@router.get("/impact", response_model=LineageImpactSummary)
def lineage_node_impact(
    session: SessionDependency,
    node_id: Annotated[str, Query(alias="nodeId", min_length=1)],
) -> LineageImpactSummary:
    try:
        return lineage_impact(session, node_id)
    except (SQLAlchemyError, OSError, ValueError, TypeError) as error:
        raise _unavailable(error) from error


@router.get("/fields/summary", response_model=FieldLineageSummary)
def field_lineage_graph(
    session: SessionDependency,
    focus_field_id: Annotated[str | None, Query(alias="focusFieldId")] = None,
) -> FieldLineageSummary:
    try:
        return field_lineage_summary(session, focus_field_id=focus_field_id)
    except (SQLAlchemyError, OSError, ValueError, TypeError) as error:
        raise _unavailable(error) from error


@router.get("/fields/impact", response_model=FieldLineageImpactSummary)
def field_lineage_field_impact(
    session: SessionDependency,
    field_id: Annotated[str, Query(alias="fieldId", min_length=1)],
) -> FieldLineageImpactSummary:
    try:
        return field_lineage_impact(session, field_id)
    except (SQLAlchemyError, OSError, ValueError, TypeError) as error:
        raise _unavailable(error) from error


@router.get("/trust/summary", response_model=LineageTrustSummary)
def lineage_trust_overlay(session: SessionDependency) -> LineageTrustSummary:
    try:
        return lineage_trust_summary(session)
    except (SQLAlchemyError, OSError, ValueError, TypeError) as error:
        raise _unavailable(error) from error


@router.get("/runtime/summary", response_model=RuntimeLineageSummary)
def lineage_runtime_execution(
    session: SessionDependency,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RuntimeLineageSummary:
    try:
        return runtime_lineage_summary(session, settings)
    except (SQLAlchemyError, OSError, ValueError, TypeError) as error:
        raise _unavailable(error) from error
