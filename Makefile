.PHONY: help up down restart build logs migrate migration-create migration-history test test-local format lint clean dbt dbt-deps dbt-seed dbt-run dbt-test dbt-clean dbt-build

# Default command shows help
help:
	@echo "=============================================================================="
	@echo "Qolyx Developer Makefile Shortcuts"
	@echo "=============================================================================="
	@echo "up                 - Start db, cache, and backend containers in background"
	@echo "down               - Stop and remove containers, networks, and volumes"
	@echo "restart            - Restart the services"
	@echo "build              - Force rebuild backend container"
	@echo "logs               - View and tail backend logs"
	@echo "migrate            - Apply all pending database migrations inside Docker"
	@echo "migration-create   - Create a new migration file. Usage: make migration-create name=<migration_name>"
	@echo "migration-history  - Show Alembic migration history inside Docker"
	@echo "test               - Run all pytest test suites inside running backend container"
	@echo "test-local         - Run pytest locally (requires local env configuration)"
	@echo "format             - Automatically format backend source code using black & isort"
	@echo "lint               - Validate python static analysis rules via flake8 & mypy"
	@echo "clean              - Wipe all transient build, cache, and compiled file relics"
	@echo "dbt                - Run a custom dbt command. Usage: make dbt cmd=\"<command>\""
	@echo "dbt-deps           - Install dbt packages and dependencies"
	@echo "dbt-seed           - Run dbt seeds with full-refresh"
	@echo "dbt-run            - Run bronze+ dbt models"
	@echo "dbt-test           - Run dbt tests and store failures"
	@echo "dbt-clean          - Clean dbt artifacts"
	@echo "dbt-build          - Run dbt build (seeds, runs, and tests)"
	@echo "=============================================================================="

up:
	docker compose --env-file .env -f infra/compose.yaml up -d

down:
	docker compose --env-file .env -f infra/compose.yaml down -v

restart:
	docker compose --env-file .env -f infra/compose.yaml restart

build:
	docker compose --env-file .env -f infra/compose.yaml build --no-cache

logs:
	docker compose --env-file .env -f infra/compose.yaml logs -f qolyx-backend

migrate:
	docker compose --env-file .env -f infra/compose.yaml exec qolyx-backend alembic upgrade head

migration-create:
	@if [ -z "$(name)" ]; then \
		echo "Error: name is required. Usage: make migration-create name=my_migration_name"; \
		exit 1; \
	fi
	docker compose --env-file .env -f infra/compose.yaml exec qolyx-backend alembic revision --autogenerate -m "$(name)"

migration-history:
	docker compose --env-file .env -f infra/compose.yaml exec qolyx-backend alembic history --verbose

test:
	docker compose --env-file .env -f infra/compose.yaml exec qolyx-backend pytest

test-local:
	pytest

format:
	docker compose --env-file .env -f infra/compose.yaml exec qolyx-backend black .
	docker compose --env-file .env -f infra/compose.yaml exec qolyx-backend isort .

lint:
	docker compose --env-file .env -f infra/compose.yaml exec qolyx-backend flake8 .
	docker compose --env-file .env -f infra/compose.yaml exec qolyx-backend mypy .

clean:
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

dbt:
	docker compose --env-file .env -f infra/compose.yaml run --rm qolyx-dbt dbt $(cmd)

dbt-deps:
	docker compose --env-file .env -f infra/compose.yaml run --rm qolyx-dbt dbt deps

dbt-seed:
	docker compose --env-file .env -f infra/compose.yaml run --rm qolyx-dbt dbt seed --full-refresh

dbt-run:
	docker compose --env-file .env -f infra/compose.yaml run --rm qolyx-dbt dbt run --models bronze+

dbt-test:
	docker compose --env-file .env -f infra/compose.yaml run --rm qolyx-dbt dbt test --store-failures

dbt-clean:
	docker compose --env-file .env -f infra/compose.yaml run --rm qolyx-dbt dbt clean

dbt-build:
	docker compose --env-file .env -f infra/compose.yaml run --rm qolyx-dbt dbt build
