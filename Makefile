# DynaDock Makefile
.PHONY: help install dev test test-unit test-integration test-examples test-watch lint format docs docs-serve clean docker-test security release pre-commit coverage-report benchmark check-deps update-deps free-port-80 example-simple example-api example-fullstack example-clean dynadock-up dynadock-down dynadock-logs dynadock-health

PYTHON := python3
UV := uv
PROJECT_NAME := dynadock
VERSION := $(shell grep version pyproject.toml | head -1 | cut -d'"' -f2)

# Colours
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: free-port-80
free-port-80: ## Find and kill the process blocking port 80
	@echo "Attempting to free port 80..."
	@./scripts/free_port.sh 80

help: ## Show this help message
	@echo "$(BLUE)DynaDock Development Commands$(NC)" && echo "" && \
	grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-25s %s\n", $$1, $$2}' | \
	sort

install: ## Install runtime dependencies only
	@echo "$(YELLOW)Installing runtime dependencies...$(NC)"
	$(UV) pip install .
	@echo "$(GREEN)✓ Installed$(NC)"

dev: ## Install development dependencies
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	$(UV) pip install -e ".[dev]"
	$(UV) pip install pytest pytest-cov pytest-asyncio pytest-docker black ruff mypy pytest-watch bandit safety pytest-timeout requests
	@chmod +x scripts/test_runner.sh
	@echo "$(GREEN)✓ Development environment ready$(NC)"

test: ## Run all tests with coverage
	@echo "$(YELLOW)Running tests...$(NC)"
	$(UV) run pytest tests/ -v --cov=src/dynadock --cov-report=term-missing --cov-report=html
	@$(MAKE) test-examples
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-unit: ## Run unit tests only
	$(UV) run pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests only
	$(UV) run pytest tests/integration/ -v -m integration

test-examples: ## Run tests for all example applications
	@echo "$(YELLOW)Testing example applications...$(NC)"
	@chmod +x scripts/test_runner.sh
	@./scripts/test_runner.sh all
	@echo "$(GREEN)✓ Example tests complete$(NC)"

test-watch: ## Run tests in watch mode
	$(UV) run pytest-watch tests/ -v

lint: ## Run linting checks (ruff + mypy)
	@echo "$(YELLOW)Running linters...$(NC)"
	$(UV) run ruff check src/ tests/
	$(UV) run mypy src/dynadock --ignore-missing-imports
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black and ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(UV) run black src/ tests/
	$(UV) run ruff check --fix src/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

docs: ## Build static documentation
	@echo "$(YELLOW)Building documentation...$(NC)"
	cd docs && $(UV) run mkdocs build
	@echo "$(GREEN)✓ Documentation built in docs/site/$(NC)"

docs-serve: ## Serve documentation locally at http://localhost:8000
	cd docs && $(UV) run mkdocs serve

clean: ## Clean build, cache and temporary files
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/ .dynadock/ .env.dynadock Caddyfile
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@$(MAKE) example-clean
	@echo "$(GREEN)✓ Clean complete$(NC)"

docker-test: ## Run integration tests inside Docker
	docker-compose -f tests/fixtures/docker-compose.test.yaml up -d
	$(UV) run pytest tests/integration/ -v -m docker
	docker-compose -f tests/fixtures/docker-compose.test.yaml down -v

security: ## Run security scanners (bandit & safety)
	$(UV) run bandit -r src/dynadock
	$(UV) run safety check

release: ## Build and publish a release
	@echo "$(YELLOW)Creating release $(VERSION)...$(NC)"
	uv build
	docker build -t $(PROJECT_NAME):$(VERSION) -t $(PROJECT_NAME):latest .
	@echo "$(GREEN)✓ Release artifacts built$(NC)"

pre-commit: format lint test ## Run all checks before committing
	@echo "$(GREEN)✓ Ready to commit!$(NC)"

coverage-report: ## Generate HTML coverage report and open it
	$(UV) run pytest tests/ --cov=src/dynadock --cov-report=html
	@echo "$(GREEN)✓ Coverage HTML generated at htmlcov/index.html$(NC)"

benchmark: ## Run performance benchmarks
	$(UV) run pytest tests/benchmarks/ -v --benchmark-only

check-deps: ## List outdated dependencies
	$(UV) pip list --outdated

update-deps: ## Upgrade dependencies to latest versions
	$(UV) pip install --upgrade pip
	$(UV) pip install -e . --upgrade

free-port-80: ## Free up port 80 for Caddy
	@echo "$(YELLOW)Freeing port 80...$(NC)"
	@sudo lsof -t -i :80 -sTCP:LISTEN | xargs -r sudo kill -9 || true
	@docker ps --filter "publish=80" --format "{{.ID}}" | xargs -r docker stop || true
	@echo "$(GREEN)✓ Port 80 is now free$(NC)"

example-simple: ## Run the simple-web example
	@echo "$(YELLOW)Starting simple-web example...$(NC)"
	cd examples/simple-web && dynadock up --enable-tls

example-api: ## Run the REST API example
	@echo "$(YELLOW)Starting REST API example...$(NC)"
	cd examples/rest-api && dynadock up --enable-tls

example-fullstack: ## Run the fullstack example
	@echo "$(YELLOW)Starting fullstack example...$(NC)"
	cd examples/fullstack && dynadock up --enable-tls

example-clean: ## Clean all example Docker resources
	@echo "$(YELLOW)Cleaning example resources...$(NC)"
	@for dir in examples/*/; do \
		if [ -f "$$dir/docker-compose.yaml" ]; then \
			cd "$$dir" && dynadock down -v 2>/dev/null || true; \
		fi; \
	done
	@echo "$(GREEN)✓ Examples cleaned$(NC)"

dynadock-up: ## Start DynaDock with current docker-compose.yaml
	@echo "$(YELLOW)Starting DynaDock services...$(NC)"
	dynadock up --enable-tls

dynadock-down: ## Stop DynaDock services
	@echo "$(YELLOW)Stopping DynaDock services...$(NC)"
	dynadock down

dynadock-logs: ## View DynaDock service logs
	dynadock logs -f

dynadock-health: ## Run health checks on DynaDock services
	@echo "$(YELLOW)Running health checks...$(NC)"
	$(PYTHON) health_check.py
	@echo "$(GREEN)✓ Health check complete$(NC)"

.DEFAULT_GOAL := help
