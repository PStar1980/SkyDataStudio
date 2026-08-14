# Analytics contracts

This directory holds source-controlled analytical-consumer and analytical-product declarations.

Phase 8.5 uses top-level consumer declarations only for lineage and impact analysis. A consumer declaration says which governed semantic model, metrics, and dimensions a downstream report requires. It does **not** claim that a Power BI workspace, semantic model, report, refresh schedule, or deployment has already been provisioned.

Phase 9 adds `products/` contracts that compose physical mart freshness, dbt build evidence, quality policy, semantic definitions, and declared consumers into an explicit publication-readiness gate. These contracts still do not represent Power BI deployment state; live Power BI service provisioning and refresh/deployment evidence remain Phase 10 responsibilities.
