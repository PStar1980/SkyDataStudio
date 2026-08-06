-- Phase 3.1: SkyData Studio metadata registry foundation.
-- The SQL mirrors the SQLAlchemy models and is intentionally PostgreSQL-compatible.

CREATE TABLE IF NOT EXISTS metadata_domain (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata_system (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    system_type VARCHAR(40) NOT NULL DEFAULT 'APPLICATION',
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata_connection (
    id VARCHAR(36) PRIMARY KEY,
    system_id VARCHAR(36) NOT NULL REFERENCES metadata_system(id),
    code VARCHAR(64) NOT NULL,
    name VARCHAR(160) NOT NULL,
    connection_type VARCHAR(40) NOT NULL DEFAULT 'API',
    environment VARCHAR(40) NOT NULL DEFAULT 'development',
    endpoint_label VARCHAR(255),
    database_name VARCHAR(128),
    secret_reference VARCHAR(160),
    read_only BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_metadata_connection UNIQUE (system_id, code)
);

CREATE TABLE IF NOT EXISTS metadata_namespace (
    id VARCHAR(36) PRIMARY KEY,
    system_id VARCHAR(36) NOT NULL REFERENCES metadata_system(id),
    connection_id VARCHAR(36) REFERENCES metadata_connection(id),
    code VARCHAR(96) NOT NULL,
    name VARCHAR(160) NOT NULL,
    namespace_type VARCHAR(40) NOT NULL DEFAULT 'SCHEMA',
    physical_name VARCHAR(255),
    environment VARCHAR(40) NOT NULL DEFAULT 'development',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_metadata_namespace UNIQUE (system_id, code)
);

CREATE TABLE IF NOT EXISTS metadata_asset (
    id VARCHAR(36) PRIMARY KEY,
    domain_id VARCHAR(36) NOT NULL REFERENCES metadata_domain(id),
    system_id VARCHAR(36) NOT NULL REFERENCES metadata_system(id),
    namespace_id VARCHAR(36) NOT NULL REFERENCES metadata_namespace(id),
    code VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    asset_type VARCHAR(40) NOT NULL DEFAULT 'TABLE',
    layer VARCHAR(40) NOT NULL DEFAULT 'RAW',
    physical_name VARCHAR(255),
    owner_name VARCHAR(160),
    owner_email VARCHAR(255),
    classification VARCHAR(40) NOT NULL DEFAULT 'INTERNAL',
    criticality VARCHAR(40) NOT NULL DEFAULT 'STANDARD',
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    source_system_code VARCHAR(64),
    source_asset_code VARCHAR(128),
    source_contract_version VARCHAR(80),
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_metadata_asset_namespace_code UNIQUE (namespace_id, code)
);

CREATE TABLE IF NOT EXISTS metadata_field (
    id VARCHAR(36) PRIMARY KEY,
    asset_id VARCHAR(36) NOT NULL REFERENCES metadata_asset(id) ON DELETE CASCADE,
    code VARCHAR(128) NOT NULL,
    name VARCHAR(160) NOT NULL,
    data_type VARCHAR(80) NOT NULL,
    ordinal_position INTEGER NOT NULL DEFAULT 1,
    nullable BOOLEAN NOT NULL DEFAULT TRUE,
    key_field BOOLEAN NOT NULL DEFAULT FALSE,
    classification VARCHAR(40),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_metadata_field UNIQUE (asset_id, code)
);

CREATE TABLE IF NOT EXISTS metadata_dependency (
    id VARCHAR(36) PRIMARY KEY,
    upstream_asset_id VARCHAR(36) NOT NULL REFERENCES metadata_asset(id),
    downstream_asset_id VARCHAR(36) NOT NULL REFERENCES metadata_asset(id),
    dependency_type VARCHAR(40) NOT NULL DEFAULT 'TRANSFORMS',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_metadata_dependency UNIQUE (
        upstream_asset_id,
        downstream_asset_id,
        dependency_type
    )
);

CREATE INDEX IF NOT EXISTS ix_metadata_asset_layer ON metadata_asset(layer);
CREATE INDEX IF NOT EXISTS ix_metadata_asset_domain_id ON metadata_asset(domain_id);
CREATE INDEX IF NOT EXISTS ix_metadata_asset_system_id ON metadata_asset(system_id);
CREATE INDEX IF NOT EXISTS ix_metadata_asset_namespace_id ON metadata_asset(namespace_id);
