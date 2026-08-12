# Studio Quality Contracts

Phase 7.2 introduces source-controlled quality gates without copying dbt test definitions into a second metadata store.

A quality contract declares the evidence a downstream consumer requires from the latest dbt build. Rule selectors reference stable evidence attributes such as target model, quality dimension, test kind, and column rather than dbt-generated test unique IDs.

## First proof contract

`fed_funds_rate_daily.v1.json` protects the governed `fct_fed_funds_rate_daily` mart with five required checks:

- observation date completeness;
- rate completeness;
- observation date uniqueness;
- rate-direction validity;
- the singular Federal Funds Rate reasonableness rule.

The contract uses `BLOCK` enforcement and requires a 100% pass rate. The contract definition is versioned in source control; latest execution evidence still comes from dbt `manifest.json` plus `run_results.json`.

## Reliability objective

The governed Federal Funds Rate daily contract also carries a Phase 7.4 SLO policy: a 30-day observation window with a 99% minimum compliant-observation rate. Studio persists one SLO observation per dbt invocation, so repeated reconciliation of identical evidence cannot inflate reliability history.
