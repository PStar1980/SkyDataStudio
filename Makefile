.PHONY: setup api web test lint format validate repo-map repo-zip

setup:
	uv sync --dev
	cd apps/web && npm install

api:
	uv run uvicorn skydata_studio.main:app --app-dir apps/api --reload --port 8100

web:
	cd apps/web && npm run dev

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy apps/api packages/contracts

format:
	uv run ruff format .
	uv run ruff check --fix .

validate:
	uv run python scripts/validate.py

repo-map:
	uv run python scripts/generate_repo_map.py

repo-zip:
	uv run python scripts/generate_repo_zip.py SkyDataStudio
