from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from skydata_studio.db.session import SessionDependency
from skydata_studio.schemas.quality import (
    DbtQualitySummary,
    QualityContractSummary,
    QualityIncidentAction,
    QualityIncidentRead,
    QualityIncidentReconcileResult,
    QualityIncidentSummary,
)
from skydata_studio.services.dbt_quality import dbt_quality_summary
from skydata_studio.services.quality_contracts import quality_contract_summary
from skydata_studio.services.quality_incidents import (
    QualityIncidentNotFoundError,
    QualityIncidentTransitionError,
    acknowledge_quality_incident,
    quality_incident_summary,
    reconcile_quality_incidents,
    resolve_quality_incident,
)

router = APIRouter()


def _artifact_unavailable(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=message,
    )


def _incident_storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "SkyData Studio quality incident storage is unavailable. Start studio-postgres "
            "and run uv run python scripts/bootstrap_metadata.py."
        ),
    )


@router.get("/dbt/summary", response_model=DbtQualitySummary)
def dbt_quality() -> DbtQualitySummary:
    try:
        return dbt_quality_summary()
    except (OSError, ValueError, TypeError) as error:
        raise _artifact_unavailable(
            "SkyData Studio could not read dbt quality artifacts. "
            "Run .\\scripts\\dbt.ps1 build and refresh Data Quality."
        ) from error


@router.get("/contracts/summary", response_model=QualityContractSummary)
def quality_contract() -> QualityContractSummary:
    try:
        return quality_contract_summary()
    except (OSError, ValueError, TypeError) as error:
        raise _artifact_unavailable(
            "SkyData Studio could not evaluate the quality contract. "
            "Confirm the source-controlled contract exists, run .\\scripts\\dbt.ps1 build, "
            "and refresh Contracts."
        ) from error


@router.get("/incidents/summary", response_model=QualityIncidentSummary)
def incident_summary(session: SessionDependency) -> QualityIncidentSummary:
    try:
        return quality_incident_summary(session)
    except SQLAlchemyError as error:
        raise _incident_storage_unavailable() from error
    except (OSError, ValueError, TypeError) as error:
        raise _artifact_unavailable(
            "SkyData Studio could not evaluate current quality evidence for incidents. "
            "Run .\\scripts\\dbt.ps1 build and retry."
        ) from error


@router.post("/incidents/reconcile", response_model=QualityIncidentReconcileResult)
def incident_reconcile(session: SessionDependency) -> QualityIncidentReconcileResult:
    try:
        return reconcile_quality_incidents(session)
    except SQLAlchemyError as error:
        session.rollback()
        raise _incident_storage_unavailable() from error
    except (OSError, ValueError, TypeError) as error:
        session.rollback()
        raise _artifact_unavailable(
            "SkyData Studio could not reconcile durable incidents from current quality evidence."
        ) from error


@router.post("/incidents/{incident_id}/acknowledge", response_model=QualityIncidentRead)
def incident_acknowledge(
    incident_id: str,
    payload: QualityIncidentAction,
    session: SessionDependency,
) -> QualityIncidentRead:
    try:
        return acknowledge_quality_incident(session, incident_id, payload)
    except QualityIncidentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except QualityIncidentTransitionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _incident_storage_unavailable() from error


@router.post("/incidents/{incident_id}/resolve", response_model=QualityIncidentRead)
def incident_resolve(
    incident_id: str,
    payload: QualityIncidentAction,
    session: SessionDependency,
) -> QualityIncidentRead:
    try:
        return resolve_quality_incident(session, incident_id, payload)
    except QualityIncidentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except QualityIncidentTransitionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise _incident_storage_unavailable() from error
