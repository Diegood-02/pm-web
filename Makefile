.PHONY: up down test lint migrate

up:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && python -m pytest
	cd frontend && npm test

lint:
	cd backend && python -m ruff check . && python -m ruff format --check . && python -m mypy
	cd frontend && npm run lint

migrate:
	docker compose exec api alembic upgrade head
