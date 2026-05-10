SHELL := /bin/bash
COMPOSE ?= docker compose
PROJECT ?= teacher

.PHONY: build up down restart logs ps test lint clean pull setup truncate-log prepare-demo-log

build:
	$(COMPOSE) build

up: prepare-demo-log
	$(COMPOSE) up -d --build

restart: prepare-demo-log
	$(COMPOSE) down
	$(COMPOSE) up -d --build

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

prepare-demo-log:
	@mkdir -p infrastructure/demo-logs
	@touch infrastructure/demo-logs/teacher-flow.log
	@chmod 777 infrastructure/demo-logs
	@chmod 666 infrastructure/demo-logs/teacher-flow.log

truncate-log: prepare-demo-log
	@rm -f infrastructure/demo-logs/teacher-flow.log
	@touch infrastructure/demo-logs/teacher-flow.log
	@chmod 666 infrastructure/demo-logs/teacher-flow.log

lint:
	./scripts/test.sh lint

# Placeholder test target; will fan out to service-specific suites as implemented
test:
	./scripts/test.sh run

bootstrap-es:
	scripts/bootstrap-elasticsearch.sh
