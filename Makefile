COMPOSE := docker compose --env-file .env -f infra/docker/docker-compose.yml

.PHONY: up down build restart clean logs logs-api logs-worker logs-web ps health \
        migrate migration seed reset-db test test-api test-smoke shell-api shell-db help

## ── Lifecycle ────────────────────────────────────────

up:              ## Start all services (detached)
	$(COMPOSE) up -d

down:            ## Stop all services
	$(COMPOSE) down

build:           ## Build and start all services
	$(COMPOSE) up --build -d

restart:         ## Restart all services
	$(COMPOSE) restart

clean:           ## Stop and remove volumes (full reset)
	$(COMPOSE) down -v

## ── Logs ─────────────────────────────────────────────

logs:            ## Tail all logs
	$(COMPOSE) logs -f

logs-api:        ## Tail API logs
	$(COMPOSE) logs -f api

logs-worker:     ## Tail Worker logs
	$(COMPOSE) logs -f worker

logs-web:        ## Tail Web logs
	$(COMPOSE) logs -f web

## ── Status ───────────────────────────────────────────

ps:              ## Show running services
	$(COMPOSE) ps

health:          ## Check API health
	@curl -sf http://localhost:8000/api/health | python -m json.tool || echo "API not reachable"

## ── Database ─────────────────────────────────────────

migrate:         ## Run alembic migrations
	$(COMPOSE) exec api alembic upgrade head

migration:       ## Create new migration (usage: make migration msg="description")
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(msg)"

seed:            ## Seed style presets + demo project
	$(COMPOSE) exec api python cli.py seed

reset-db:        ## Drop all tables, recreate, migrate, and seed
	$(COMPOSE) exec api alembic downgrade base || true
	$(COMPOSE) exec api alembic upgrade head
	$(COMPOSE) exec api python cli.py seed
	@echo "Database reset complete"

## ── Testing ──────────────────────────────────────────

test:            ## Run all tests (inside API container)
	$(COMPOSE) exec api python -m pytest tests/ -v --tb=short

test-smoke:      ## Run API smoke tests only
	$(COMPOSE) exec api python -m pytest tests/test_smoke.py -v

## ── Shell Access ─────────────────────────────────────

shell-api:       ## Open shell in API container
	$(COMPOSE) exec api /bin/sh

shell-db:        ## Open psql in postgres container
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-reelsmaker} -d $${POSTGRES_DB:-reelsmaker}

## ── Help ─────────────────────────────────────────────

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
