# Roadmap Notes

The canonical implementation roadmap is maintained in the root `README.md` so GitHub visitors immediately understand the product direction.

## Phase 1.2 — Green Validation Baseline

**Status:** Implemented locally; pending SkyCommand promotion and GitHub proof.

Changes:

- backend Ruff import and line-length findings repaired;
- JSX component references registered with ESLint without introducing another package dependency;
- mobile navigation state update removed from the pathname effect;
- local validation expanded to Python compilation, dependency synchronization, Ruff, mypy, pytest, ESLint, and Vite build;
- first local validation generates `uv.lock` and `apps/web/package-lock.json`;
- subsequent local and GitHub runs consume locked dependencies;
- GitHub Actions upgraded to current Node 24-compatible action generations;
- GitHub workflow concurrency now cancels superseded validation runs.

Acceptance evidence required for closure:

- local `python scripts/validate.py` succeeds;
- `uv.lock` and `apps/web/package-lock.json` are committed;
- PR backend and frontend checks succeed;
- post-merge `main` backend and frontend checks succeed;
- local and remote `main`/`dev` references are synchronized.

This file remains the home for phase-level decisions, acceptance evidence, and closure summaries as development proceeds.
