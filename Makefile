# DynaDock Makefile
.PHONY: help install dev test test-unit test-integration test-examples test-watch lint format docs docs-serve clean docker-test security release pre-commit coverage-report benchmark check-deps update-deps free-port-80 example-simple example-api example-fullstack example-clean dynadock-up dynadock-down dynadock-logs dynadock-health build-dist check-dist publish publish-testpypi

PYTHON := python3
UV := uv
PROJECT_NAME := dynadock
# Read version dynamically from src/dynadock/__init__.py (__version__ = "x.y.z")
VERSION := $(shell awk -F\" '/^__version__/ {print $$2}' src/dynadock/__init__.py)

# Colours
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

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
	$(UV) pip install -e .
	$(UV) pip install pytest pytest-cov pytest-asyncio pytest-docker black ruff mypy pytest-watch bandit safety pytest-timeout requests twine
	@echo "$(GREEN)✓ Development environment ready$(NC)"

test: ## Run all tests with coverage
	@echo "$(YELLOW)Running tests...$(NC)"
	@bash ./scripts/run_pytests.sh
	@$(MAKE) test-examples
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-unit: ## Run unit tests only
	$(UV) run pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests only
	$(UV) run pytest tests/integration/ -v -m integration

test-examples: ## Run tests for all example applications
	@echo "$(YELLOW)Testing example applications...$(NC)"
	@./scripts/test_runner.sh all
	@echo "$(GREEN)✓ Example tests complete$(NC)"

test-watch: ## Run tests in watch mode
	bash ./scripts/watch_tests.sh

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

clean: ## Clean all build, cache, and temporary files (including root-owned)
	@echo "$(YELLOW)Cleaning build artifacts and temporary files...$(NC)"
	@bash ./scripts/examples_clean.sh
	@bash ./scripts/clean_artifacts.sh
	@echo "$(GREEN)✓ Clean complete$(NC)"

docker-test: ## Run integration tests inside Docker
	@bash ./scripts/docker_test.sh

security: ## Run security scanners (bandit & safety)
	$(UV) run bandit -r src/dynadock
	$(UV) run safety check

release: ## Build and publish a release
	@echo "$(YELLOW)Creating release $(VERSION)...$(NC)"
	uv build
	docker build -t $(PROJECT_NAME):$(VERSION) -t $(PROJECT_NAME):latest .
	@echo "$(GREEN)✓ Release artifacts built$(NC)"

# ---------------------------
# PyPI publishing helpers
# ---------------------------

build-dist: ## Build sdist and wheel into dist/
	uv build

check-dist: ## Check built distributions with twine
	$(UV) run --with twine twine check dist/*



build:
	$(PY) -m build

test-e2e:
	@echo "Using PY=$(PY)"
	@echo "LIBVIRT_DEFAULT_URI=$(LIBVIRT_DEFAULT_URI)"
	@echo "dynadock_TEST_IMAGE=$(dynadock_TEST_IMAGE)"
	@echo "dynadock_TEST_OS_VARIANT=$(dynadock_TEST_OS_VARIANT)"
	$(PY) -m pytest -v tests/test_e2e.py

# Versioning
version-show: ## Show the current version
	@hatch version show

version-patch: ## Bump the patch version
	@hatch version patch

version-minor: ## Bump the minor version
	@hatch version minor

version-major: ## Bump the major version
	@hatch version major

# Publishing with automatic versioning
publish: ## Automatically bump patch version, build, tag, and publish to PyPI
	if [ "$$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then \
		echo "$(RED)Not on main branch. Please switch to main before publishing.$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Bumping patch version...$(NC)"
	@CURRENT_VERSION=$$(shell awk -F\" '/^__version__/ {print $$2}' src/dynadock/__init__.py); \
	NEW_VERSION=$$(echo $$CURRENT_VERSION | awk -F. -v OFS=. '{$$3++; print}'); \
	sed -i "s/__version__ = \"$$CURRENT_VERSION\"/__version__ = \"$$NEW_VERSION\"/" src/dynadock/__init__.py; \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo "Version bumped from $$CURRENT_VERSION to $$NEW_VERSION"
	NEW_VERSION=v$$(shell awk -F\" '/^__version__/ {print $$2}' src/dynadock/__init__.py);
	echo "$(YELLOW)Building and checking distribution...$(NC)"
	$(MAKE) build-dist
	$(MAKE) check-dist
	echo "$(YELLOW)Committing version bump...$(NC)"
	git commit -am "chore: Bump version to $$NEW_VERSION"
	echo "$(YELLOW)Tagging new version $$NEW_VERSION...$(NC)"
	git tag "$$NEW_VERSION"
	echo "$(YELLOW)Pushing commit and tags...$(NC)"
	git push && git push --tags
	echo "$(YELLOW)Publishing to PyPI...$(NC)"
	$(UV) run --with twine twine upload dist/*
	echo "$(GREEN)✓ Successfully published version $$NEW_VERSION to PyPI!$(NC)"

publish-testpypi: ## Upload package to TestPyPI (requires TESTPYPI_TOKEN env var)
	uv build
	$(UV) run --with twine twine check dist/*
	$(UV) run --with twine twine upload -r testpypi dist/*

publish-pypi: version-patch ## Upload package to PyPI (requires PYPI_TOKEN env var)
	uv build
	$(UV) run --with twine twine check dist/*
	$(UV) run --with twine twine upload dist/*

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
	@bash ./scripts/free_port_80.sh

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
	@bash ./scripts/examples_clean.sh

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
