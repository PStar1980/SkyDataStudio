from fastapi import APIRouter

from skydata_contracts.skycommand import ConsumerContract

router = APIRouter()

CONTRACTS = [
    ConsumerContract(
        code="data_catalogue.v1",
        purpose="Discover domains, sources, assets, metrics, dependencies, and metadata.",
    ),
    ConsumerContract(
        code="data_asset.v1",
        purpose="Resolve portable asset identity and source/storage bindings.",
    ),
    ConsumerContract(
        code="data_freshness_status.v1",
        purpose="Consume explainable freshness evidence before downstream processing.",
    ),
    ConsumerContract(
        code="ingestion_run_summary.v1",
        purpose="Consume durable run, attempt, row-count, quality, and outcome evidence.",
    ),
    ConsumerContract(
        code="ingestion_quality_evidence.v1",
        purpose="Consume ingestion quality, revision, and rejected-row evidence.",
    ),
]


@router.get("/skycommand", response_model=list[ConsumerContract])
def skycommand_contracts() -> list[ConsumerContract]:
    return CONTRACTS
