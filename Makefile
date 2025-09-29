SHELL := /bin/bash
COMPOSE ?= docker compose
PROJECT ?= teacher

.PHONY: build up down restart logs ps test lint clean pull setup

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

restart:
	$(COMPOSE) down
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

setup:
	@[ -f .env ] || (echo "Copying .env.dist to .env" && cp .env.dist .env)

pull:
	$(COMPOSE) pull

clean:
	$(COMPOSE) down -v --remove-orphans

lint:
	./scripts/test.sh lint

# Placeholder test target; will fan out to service-specific suites as implemented
test:
	./scripts/test.sh run
