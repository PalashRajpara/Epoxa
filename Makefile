.PHONY: help install test test-coverage run-backend run-frontend build-frontend migration-target migrate seed cleanup

help:
	@echo "Epoxa Platform Automation Commands"
	@echo "  make install         Install backend and frontend dependencies"
	@echo "  make test            Run full backend test suite"
	@echo "  make run-backend     Start FastAPI backend server on :8000"
	@echo "  make run-frontend    Start Vite React dev server on :5173"
	@echo "  make build-frontend  Build production frontend bundle"
	@echo "  make migration-target Inspect configured database target safely"
	@echo "  make migrate         Run Alembic migrations upgrade head"
	@echo "  make seed            Seed synthetic demo organization & data"
	@echo "  make cleanup         Run 30-day transcript retention cleanup"

install:
	uv --no-config pip install --python ./.venv/bin/python -r pyproject.toml
	npm install --prefix frontend

test:
	PYTHONPATH=backend ./.venv/bin/pytest --rootdir . -c backend/pytest.ini backend/tests -v

run-backend:
	PYTHONPATH=backend ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

run-frontend:
	npm run dev --prefix frontend

run-customer:
	npm run dev:customer --prefix frontend

run-supervisor:
	npm run dev:supervisor --prefix frontend

build-frontend:
	npm run build --prefix frontend

migration-target:
	PYTHONPATH=backend ./.venv/bin/python backend/app/scripts/verify_db_target.py

migrate:
	PYTHONPATH=backend ./.venv/bin/alembic -c backend/alembic.ini upgrade head

seed:
	PYTHONPATH=backend ./.venv/bin/python backend/app/scripts/seed_demo.py

cleanup:
	PYTHONPATH=backend ./.venv/bin/python backend/app/scripts/cleanup_retention.py
