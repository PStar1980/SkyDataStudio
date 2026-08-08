-- Phase 4.1: versioned pipeline definitions, parameters, steps, and dependency graph.

CREATE TABLE IF NOT EXISTS pipeline_definition (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(160) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    environment VARCHAR(40) NOT NULL DEFAULT 'development',
    execution_mode VARCHAR(40) NOT NULL DEFAULT 'LOCAL',
    mapping_id VARCHAR(36) REFERENCES metadata_mapping(id),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_version (
    id VARCHAR(36) PRIMARY KEY,
    pipeline_id VARCHAR(36) NOT NULL REFERENCES pipeline_definition(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    notes TEXT,
    execution_contract JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_version_number UNIQUE (pipeline_id, version_number)
);

CREATE TABLE IF NOT EXISTS pipeline_parameter (
    id VARCHAR(36) PRIMARY KEY,
    version_id VARCHAR(36) NOT NULL REFERENCES pipeline_version(id) ON DELETE CASCADE,
    code VARCHAR(128) NOT NULL,
    name VARCHAR(160) NOT NULL,
    data_type VARCHAR(40) NOT NULL DEFAULT 'STRING',
    required BOOLEAN NOT NULL DEFAULT FALSE,
    default_value JSONB,
    ordinal_position INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_parameter_code UNIQUE (version_id, code)
);

CREATE TABLE IF NOT EXISTS pipeline_step (
    id VARCHAR(36) PRIMARY KEY,
    version_id VARCHAR(36) NOT NULL REFERENCES pipeline_version(id) ON DELETE CASCADE,
    code VARCHAR(128) NOT NULL,
    name VARCHAR(200) NOT NULL,
    step_type VARCHAR(40) NOT NULL DEFAULT 'SQL',
    execution_order INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(40) NOT NULL DEFAULT 'READY',
    mapping_id VARCHAR(36) REFERENCES metadata_mapping(id),
    source_asset_id VARCHAR(36) REFERENCES metadata_asset(id),
    target_asset_id VARCHAR(36) REFERENCES metadata_asset(id),
    sql_text TEXT,
    script_path VARCHAR(500),
    timeout_seconds INTEGER NOT NULL DEFAULT 300,
    retry_count INTEGER NOT NULL DEFAULT 0,
    continue_on_failure BOOLEAN NOT NULL DEFAULT FALSE,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_step_code UNIQUE (version_id, code)
);

CREATE TABLE IF NOT EXISTS pipeline_step_dependency (
    id VARCHAR(36) PRIMARY KEY,
    step_id VARCHAR(36) NOT NULL REFERENCES pipeline_step(id) ON DELETE CASCADE,
    depends_on_step_id VARCHAR(36) NOT NULL REFERENCES pipeline_step(id) ON DELETE CASCADE,
    dependency_condition VARCHAR(40) NOT NULL DEFAULT 'SUCCESS',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pipeline_step_dependency UNIQUE (step_id, depends_on_step_id),
    CONSTRAINT ck_pipeline_step_dependency_distinct CHECK (step_id <> depends_on_step_id)
);

CREATE INDEX IF NOT EXISTS ix_pipeline_definition_status ON pipeline_definition(status);
CREATE INDEX IF NOT EXISTS ix_pipeline_definition_environment ON pipeline_definition(environment);
CREATE INDEX IF NOT EXISTS ix_pipeline_definition_mapping_id ON pipeline_definition(mapping_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_version_pipeline_id ON pipeline_version(pipeline_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_parameter_version_id ON pipeline_parameter(version_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_step_version_id ON pipeline_step(version_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_step_mapping_id ON pipeline_step(mapping_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_step_dependency_step_id ON pipeline_step_dependency(step_id);
CREATE INDEX IF NOT EXISTS ix_pipeline_step_dependency_depends_on_step_id
    ON pipeline_step_dependency(depends_on_step_id);
