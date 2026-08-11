{{ config(enabled=false) }}

-- Retained only as historical scaffolding from the Phase 2 contract bridge.
-- Phase 6.1 models now begin from the Studio-owned curated relation
-- mart.fed_funds_rate rather than a placeholder synchronization table.

select
    cast(null as text) as domain_code,
    cast(null as text) as source_code,
    cast(null as text) as asset_code,
    cast(null as text) as asset_name,
    cast(null as timestamp) as synchronized_at
where false
