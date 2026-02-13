SHELL := /bin/bash

.PHONY: up down logs init-db show-demo test psql

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

init-db:
	docker compose run --rm app python -m src.main init-db

show-demo:
	docker compose run --rm app python -m src.main show-demo

test:
	docker compose run --rm app bash -lc "PYTHONPATH=/app pytest -q"

psql:
	docker compose exec database sh -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'






