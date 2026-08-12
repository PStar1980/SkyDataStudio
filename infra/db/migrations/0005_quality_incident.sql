CREATE TABLE IF NOT EXISTS quality_incident (
    id VARCHAR(36) PRIMARY KEY,
    incident_key VARCHAR(320) NOT NULL UNIQUE,
    contract_code VARCHAR(160) NOT NULL,
    contract_version VARCHAR(40) NOT NULL,
    rule_code VARCHAR(160) NOT NULL,
    rule_label VARCHAR(255) NOT NULL,
    target_name VARCHAR(255) NOT NULL,
    layer VARCHAR(40) NOT NULL,
    quality_dimension VARCHAR(60) NOT NULL,
    severity VARCHAR(40) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'OPEN',
    evidence_outcome VARCHAR(40) NOT NULL,
    matched_check_name VARCHAR(500),
    matched_status VARCHAR(40),
    message TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_detected_at TIMESTAMPTZ NOT NULL,
    last_detected_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(160),
    resolved_at TIMESTAMPTZ,
    resolution_note TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_quality_incident_contract_code
    ON quality_incident (contract_code);
CREATE INDEX IF NOT EXISTS ix_quality_incident_rule_code
    ON quality_incident (rule_code);
CREATE INDEX IF NOT EXISTS ix_quality_incident_target_name
    ON quality_incident (target_name);
CREATE INDEX IF NOT EXISTS ix_quality_incident_layer
    ON quality_incident (layer);
CREATE INDEX IF NOT EXISTS ix_quality_incident_quality_dimension
    ON quality_incident (quality_dimension);
CREATE INDEX IF NOT EXISTS ix_quality_incident_severity
    ON quality_incident (severity);
CREATE INDEX IF NOT EXISTS ix_quality_incident_status
    ON quality_incident (status);

CREATE TABLE IF NOT EXISTS quality_incident_event (
    id VARCHAR(36) PRIMARY KEY,
    incident_id VARCHAR(36) NOT NULL REFERENCES quality_incident(id) ON DELETE CASCADE,
    event_type VARCHAR(40) NOT NULL,
    actor VARCHAR(160),
    note TEXT,
    evidence_outcome VARCHAR(40),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_quality_incident_event_incident_id
    ON quality_incident_event (incident_id);
CREATE INDEX IF NOT EXISTS ix_quality_incident_event_event_type
    ON quality_incident_event (event_type);
