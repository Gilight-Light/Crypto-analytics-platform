SHELL := /bin/bash
COMPOSE := docker compose

PROFILES ?=
PROFILE_FLAGS := $(foreach p,$(PROFILES),--profile $(p))

.DEFAULT_GOAL := help
.PHONY: help env build up down restart logs ps healthcheck clean lint test

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Create .env from .env.example if missing
	@test -f .env || (cp .env.example .env && echo "Created .env from template")

build: ## Build images that have a Dockerfile (spark first; airflow image inherits from it)
	$(COMPOSE) $(PROFILE_FLAGS) build spark-master
	$(COMPOSE) $(PROFILE_FLAGS) build

up: env ## Bring up the stack (set PROFILES="..." to add optional profiles)
	$(COMPOSE) $(PROFILE_FLAGS) up -d

down: ## Stop and remove containers (volumes preserved)
	$(COMPOSE) down

restart: down up ## Restart the stack

logs: ## Tail logs for all running services
	$(COMPOSE) logs -f --tail=100

ps: ## Show container status
	$(COMPOSE) ps

healthcheck: ## Probe each service
	@bash scripts/healthcheck.sh

clean: ## Stop containers AND remove named volumes (wipes all data)
	$(COMPOSE) down -v --remove-orphans

lint: ## Run ruff + black checks
	@uv run ruff check . && uv run black --check .

test: ## Run pytest
	@uv run pytest
