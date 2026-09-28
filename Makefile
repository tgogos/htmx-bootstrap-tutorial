dotenv:
	cp .env.example .env

build:
	docker compose -f docker-compose.dev.yml build

up:
	docker compose -f docker-compose.dev.yml up

upd:
	docker compose -f docker-compose.dev.yml up -d

down:
	docker compose -f docker-compose.dev.yml down

downv:
	docker compose -f docker-compose.dev.yml down -v

test:
	docker compose -f docker-compose.dev.yml exec fastapi-htmx-bootstrap pytest

seed:
	docker compose -f docker-compose.dev.yml exec fastapi-htmx-bootstrap python -m app.seed

# Local tooling (optional; Docker remains the default workflow)
sync:
	uv sync --all-groups

lock:
	uv lock
