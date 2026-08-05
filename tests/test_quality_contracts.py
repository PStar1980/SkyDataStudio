from skydata_studio.integrations.skycommand.preview import (
    preview_quality_events,
    preview_rejection_events,
    preview_revision_events,
)


def test_quality_contract_preview_models_are_versioned() -> None:
    quality = preview_quality_events()
    revisions = preview_revision_events()
    rejections = preview_rejection_events()

    assert quality.contract_version == "ingestion_quality_evidence.v1"
    assert revisions.contract_version == "ingestion_quality_evidence.v1"
    assert rejections.contract_version == "ingestion_quality_evidence.v1"
    assert quality.items[0].event_type == "QUALITY"
    assert revisions.items[0].event_type == "REVISION"
    assert rejections.items[0].event_type == "REJECTION"
