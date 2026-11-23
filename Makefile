.PHONY: infra api worker web migrate test lint

POSTGRES_ADMIN_URL ?= postgresql://postgres:local-admin-only@localhost:5432/career_intelligence

infra:
	docker compose up -d postgres redis minio

api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

worker:
	cd apps/api && python -m app.workers.worker

web:
	cd apps/web && npm run dev

migrate:
	psql "$(POSTGRES_ADMIN_URL)" -v ON_ERROR_STOP=1 -f apps/api/migrations/0001_initial.sql
	psql "$(POSTGRES_ADMIN_URL)" -v ON_ERROR_STOP=1 -f apps/api/migrations/0002_resume_upload_state.sql
	psql "$(POSTGRES_ADMIN_URL)" -v ON_ERROR_STOP=1 -f apps/api/migrations/0003_runtime_role_and_user_rls.sql
	psql "$(POSTGRES_ADMIN_URL)" -v ON_ERROR_STOP=1 -f apps/api/migrations/0004_full_platform_extensions.sql

test:
	cd apps/api && pytest -q

lint:
	cd apps/api && ruff check app tests && mypy app
	cd apps/web && npm run lint
