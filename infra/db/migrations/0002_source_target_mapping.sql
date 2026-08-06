-- Phase 3.2: source-to-target mapping, target schema, and lineage specifications.

CREATE TABLE IF NOT EXISTS metadata_mapping (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(160) NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_asset_id VARCHAR(36) NOT NULL REFERENCES metadata_asset(id),
    target_asset_id VARCHAR(36) NOT NULL REFERENCES metadata_asset(id),
    mapping_type VARCHAR(40) NOT NULL DEFAULT 'TRANSFORM',
    load_strategy VARCHAR(40) NOT NULL DEFAULT 'FULL_REPLACE',
    status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
    grain VARCHAR(255),
    business_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
    transformation_expression TEXT,
    description TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_metadata_mapping_code UNIQUE (code),
    CONSTRAINT uq_metadata_mapping_edge UNIQUE (
        source_asset_id,
        target_asset_id,
        mapping_type
    ),
    CONSTRAINT ck_metadata_mapping_distinct_assets CHECK (
        source_asset_id <> target_asset_id
    )
);

CREATE TABLE IF NOT EXISTS metadata_field_mapping (
    id VARCHAR(36) PRIMARY KEY,
    mapping_id VARCHAR(36) NOT NULL REFERENCES metadata_mapping(id) ON DELETE CASCADE,
    source_field_code VARCHAR(128),
    target_field_code VARCHAR(128) NOT NULL,
    target_data_type VARCHAR(80) NOT NULL,
    transformation_type VARCHAR(40) NOT NULL DEFAULT 'DIRECT',
    expression TEXT,
    ordinal_position INTEGER NOT NULL DEFAULT 1,
    nullable BOOLEAN NOT NULL DEFAULT TRUE,
    key_field BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_metadata_field_mapping_target UNIQUE (
        mapping_id,
        target_field_code
    )
);

CREATE INDEX IF NOT EXISTS ix_metadata_mapping_source_asset_id
    ON metadata_mapping(source_asset_id);
CREATE INDEX IF NOT EXISTS ix_metadata_mapping_target_asset_id
    ON metadata_mapping(target_asset_id);
CREATE INDEX IF NOT EXISTS ix_metadata_mapping_status
    ON metadata_mapping(status);
CREATE INDEX IF NOT EXISTS ix_metadata_field_mapping_mapping_id
    ON metadata_field_mapping(mapping_id);
