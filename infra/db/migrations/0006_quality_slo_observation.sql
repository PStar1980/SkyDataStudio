CREATE TABLE IF NOT EXISTS quality_slo_observation (
    id VARCHAR(36) PRIMARY KEY,
    observation_key VARCHAR(420) NOT NULL UNIQUE,
    contract_code VARCHAR(160) NOT NULL,
    contract_version VARCHAR(40) NOT NULL,
    evidence_invocation_id VARCHAR(160),
    evidence_generated_at TIMESTAMPTZ,
    contract_status VARCHAR(40) NOT NULL,
    artifact_status VARCHAR(40) NOT NULL,
    evidence_trust_posture VARCHAR(40) NOT NULL,
    pass_rate DOUBLE PRECISION NOT NULL,
    active_incident_count INTEGER NOT NULL DEFAULT 0,
    blocking_active_incident_count INTEGER NOT NULL DEFAULT 0,
    warning_active_incident_count INTEGER NOT NULL DEFAULT 0,
    captured_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_quality_slo_observation_contract_code
    ON quality_slo_observation (contract_code);
CREATE INDEX IF NOT EXISTS ix_quality_slo_observation_evidence_invocation_id
    ON quality_slo_observation (evidence_invocation_id);
CREATE INDEX IF NOT EXISTS ix_quality_slo_observation_contract_status
    ON quality_slo_observation (contract_status);
CREATE INDEX IF NOT EXISTS ix_quality_slo_observation_artifact_status
    ON quality_slo_observation (artifact_status);
CREATE INDEX IF NOT EXISTS ix_quality_slo_observation_evidence_trust_posture
    ON quality_slo_observation (evidence_trust_posture);
CREATE INDEX IF NOT EXISTS ix_quality_slo_observation_captured_at
    ON quality_slo_observation (captured_at);
