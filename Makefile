.PHONY: help dev run-api run-agent run-web run-dashboard lint format test migrate seed gen-client clean

help:
	@echo "Voice AI Agent Monorepo Tasks:"
	@echo "  make dev           - Launch all local services (API, Agent, Web, Dashboard) concurrently"
	@echo "  make run-api       - Launch FastAPI Backend server (port 8000)"
	@echo "  make run-agent     - Launch Voice AI Agent LiveKit worker"
	@echo "  make run-web       - Launch Customer Voice Web Portal (port 3000)"
	@echo "  make run-dashboard - Launch Supervisor Console (port 3001)"
	@echo "  make migrate       - Run Alembic database migrations"
	@echo "  make seed          - Run idempotent database seeds"
	@echo "  make lint          - Run ruff and mypy type checks"
	@echo "  make format        - Auto-format code with ruff"
	@echo "  make test          - Run test suite"
	@echo "  make clean         - Remove cache and build artifacts"

dev:
	@echo "Launching all 4 services in parallel..."
	@make -j 4 run-api run-agent run-web run-dashboard

run-api:
	PYTHONPATH=packages/core/src:apps/api/src:$$PYTHONPATH uv run uvicorn epoxa_api.main:app --reload --port 8000

run-agent:
	PYTHONPATH=packages/core/src:apps/agent/src:$$PYTHONPATH uv run python -m epoxa_agent.main dev

run-web:
	pnpm --filter epoxa-web dev

run-dashboard:
	pnpm --filter epoxa-dashboard dev

lint:
	uv run ruff check .
	uv run mypy packages/core apps/api

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

migrate:
	PYTHONPATH=packages/core/src:$$PYTHONPATH uv run alembic -c db/alembic.ini upgrade head

seed:
	PYTHONPATH=packages/core/src:$$PYTHONPATH uv run python db/seeds/seed.py

gen-client:
	PYTHONPATH=packages/core/src:apps/api/src:$$PYTHONPATH uv run python apps/api/src/epoxa_api/scripts/export_openapi.py
	cd packages/api-client && pnpm run generate

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
