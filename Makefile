SHELL := /bin/bash
.ONESHELL:
.DEFAULT_GOAL := help

COMPOSE      := docker compose
OPA_URL  ?= http://localhost:8181
TRINO_URL ?= http://localhost:8080
PYTHON   := python3
PIP      := pip3

GREEN  := \033[0;32m
YELLOW := \033[0;33m
RESET  := \033[0m

# Commands

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

.PHONY: up
up: ## Start stack — OPAL fetches policies from GitLab, OPA enforces at query and storage layers
	$(COMPOSE) up -d --build
	@echo -e "$(YELLOW)Waiting for services to become healthy…$(RESET)"
	@$(MAKE) wait-healthy

.PHONY: down
down: ## Stop and remove all containers (both modes)
	$(COMPOSE) down -v

.PHONY: restart
restart: down up ## Full teardown and restart (dev mode)


.PHONY: opal-status
opal-status: ## Show OPAL policy sync status
	@echo "=== OPAL Server policy sources ==="
	@curl -s http://localhost:$${OPAL_SERVER_PORT:-7002}/policy | python3 -m json.tool 2>/dev/null || echo "(OPAL not running)"
	@echo ""
	@echo "=== OPA loaded policies ==="
	@$(MAKE) opa-status

# Data Generation

.PHONY: generate-data
generate-data: ## Generate synthetic banking data and upload to MinIO
	$(PIP) install -q -r data/requirements.txt
	cd data && $(PYTHON) generate.py

.PHONY: init-tables
init-tables: ## Create Iceberg schemas and tables in Trino
	@echo -e "$(YELLOW)Initialising Iceberg tables via Trino…$(RESET)"
	cat scripts/init_tables.sql | docker exec -i $$($(COMPOSE) ps -q trino) trino --server http://localhost:8080 --user admin

# OPA policy management

.PHONY: opa-check
opa-check: ## Lint / format-check all Rego files — no local OPA CLI required
	docker run --rm -v $(PWD)/policies:/policies openpolicyagent/opa fmt --diff /policies
	docker run --rm -v $(PWD)/policies:/policies openpolicyagent/opa check /policies

.PHONY: opa-status
opa-status: ## Show OPA policy store contents
	@curl -s $(OPA_URL)/v1/policies | python3 -m json.tool

# Pytest compliance scenarios

.PHONY: install-deps
install-deps: ## Install Python test dependencies
	$(PIP) install -r data/requirements.txt
	$(PIP) install pytest requests trino PyJWT boto3

.PHONY: test
test: ## Run all Pytest compliance tests
	$(PIP) install -q -r data/requirements.txt pytest requests trino PyJWT boto3
	pytest tests/ -v --tb=short

.PHONY: test-rbac
test-rbac: ## Run Scenario 1 — RBAC tests only
	pytest tests/test_rbac.py -v --tb=short

.PHONY: test-masking
test-masking: ## Run Scenario 2 — Column masking tests only
	pytest tests/test_masking.py -v --tb=short

.PHONY: test-crossdomain
test-crossdomain: ## Run Scenario 3 — Cross-domain tests only
	pytest tests/test_cross_domain.py -v --tb=short

.PHONY: test-storage
test-storage: ## Run MinIO storage-layer bypass test
	pytest tests/test_storage_layer.py -v --tb=short

# Audit / evidence capture

.PHONY: capture-logs
capture-logs: ## Capture OPA decision log snapshot to logs/
	$(PYTHON) scripts/capture_decision_log.py

.PHONY: generate-token
generate-token: ## Generate a JWT for testing (ROLE= DOMAIN= make generate-token)
	$(PYTHON) scripts/generate_token.py \
		--role  $(or $(ROLE),data-analyst) \
		--domain $(or $(DOMAIN),customer)

# Demo

.PHONY: demo
demo: ## Full demo: up -> init tables -> generate data -> compliance tests -> capture logs
	@echo -e "$(GREEN)=== Step 1/5  Starting services ===$(RESET)"
	$(MAKE) up
	@echo -e "$(GREEN)=== Step 2/5  Initialising Iceberg tables ===$(RESET)"
	$(MAKE) init-tables
	@echo -e "$(GREEN)=== Step 3/5  Generating synthetic data ===$(RESET)"
	$(MAKE) generate-data
	@echo -e "$(GREEN)=== Step 4/5  Running compliance scenario tests ===$(RESET)"
	$(MAKE) test
	@echo -e "$(GREEN)=== Step 5/5  Capturing OPA decision log ===$(RESET)"
	$(MAKE) capture-logs
	@echo -e "$(GREEN)=== Demo complete. Check logs/ for audit evidence. ===$(RESET)"

# Diagrams

.PHONY: diagrams
diagrams: ## Render PlantUML sequence diagrams to PNG (requires plantuml + java)
	plantuml diagrams/*.puml
	@echo "PNG files written to diagrams/"

# Internal helpers

.PHONY: wait-healthy
wait-healthy: ## Poll until OPA and Trino report healthy, then wait for Trino query readiness
	@for svc in "$(OPA_URL)/health" "$(TRINO_URL)/v1/info"; do \
		echo -n "  Waiting for $$svc "; \
		for i in $$(seq 1 30); do \
			if curl -sf "$$svc" > /dev/null 2>&1; then \
				echo -e " $(GREEN)OK$(RESET)"; break; \
			fi; \
			echo -n "."; sleep 3; \
		done; \
	done
	@echo -n "  Waiting for Trino query readiness "
	@for i in $$(seq 1 40); do \
		result=$$(docker exec $$($(COMPOSE) ps -q trino) trino \
			--server http://localhost:8080 --user admin \
			--execute "SHOW CATALOGS" 2>&1); \
		if echo "$$result" | grep -q "customer" && echo "$$result" | grep -q "deposits"; then \
			echo -e " $(GREEN)OK$(RESET)"; exit 0; \
		fi; \
		echo -n "."; sleep 5; \
	done; \
	echo -e " $(YELLOW)timeout — proceeding anyway$(RESET)"
