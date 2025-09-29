SHELL := /bin/bash
COMPOSE ?= docker compose

.PHONY: up down logs ps seed

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down -v --remove-orphans

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

seed:
	@echo "TODO: add sample data loading script for ${concept_name}";
