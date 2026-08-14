# Analytical product contracts

Phase 9 source-controls the declaration of an analytical product separately from its runtime evidence.
A product contract names the curated source relation, dbt mart relation, semantic model, quality gate,
governed metrics, dimensions, and declared consumers required before Studio may call the product ready.

These contracts do not represent Power BI deployment state. Phase 9 proves Studio analytical-product
readiness and publication boundaries; live Power BI workspace, report, refresh, and deployment evidence
remain Phase 10.
