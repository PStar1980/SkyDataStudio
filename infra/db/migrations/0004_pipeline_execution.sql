-- Phase 4.2: replay-safe local pipeline execution and structured run evidence.

CREATE TABLE IF NOT EXISTS pipeline_run (
    id VARCHAR(36) PRIMARY KEY,
    pipeline_id VARCHAR(36) NOT NULL REFERENCES pipeline_definition(id) ON DELETE CASCADE,
    version_id VARCHAR(36) NOT NULL REFERENCES pipeline_version(id) ON DELETE CASCADE,
    run_key VARCHAR(255) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    trigger_type VARCHAR(40) NOT NULL DEFAULT 'MANUAL',
    execution_mode VARCHAR(40) NOT NULL DEFAULT 'LOCAL',
    environment VARCHAR(40) NOT NULL DEFAULT 'development',
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    execution_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    replay_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_replayed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_run_key UNIQUE (pipeline_id, run_key)
);

CREATE TABLE IF NOT EXISTS pipeline_step_run (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL REFERENCES pipeline_run(id) ON DELETE CASCADE,
    step_id VARCHAR(36) NOT NULL REFERENCES pipeline_step(id) ON DELETE CASCADE,
    step_code VARCHAR(128) NOT NULL,
    step_name VARCHAR(200) NOT NULL,
    step_type VARCHAR(40) NOT NULL,
    execution_order INTEGER NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_step_run UNIQUE (run_id, step_id)
);

CREATE INDEX IF NOT EXISTS ix_pipeline_run_pipeline_id ON pipeline_run(pipeline_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_run_version_id ON pipeline_run(version_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_run_status ON pipeline_run(status);
CREATE INDEX IF NOT EXISTS ix_pipeline_run_environment ON pipeline_run(environment);
CREATE INDEX IF NOT EXISTS ix_pipeline_run_run_key ON pipeline_run(run_key);
CREATE INDEX IF NOT EXISTS ix_pipeline_step_run_run_id ON pipeline_step_run(run_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_step_run_step_id ON pipeline_step_run(step_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_step_run_status ON pipeline_step_run(status);
