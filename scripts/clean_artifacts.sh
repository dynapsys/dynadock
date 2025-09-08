#!/usr/bin/env bash
# Clean build, cache, and DynaDock generated files (safe to run repeatedly)
set -euo pipefail

YELLOW="\033[0;33m"
GREEN="\033[0;32m"
NC="\033[0m"

echo -e "${YELLOW}Cleaning build artifacts and temporary files...${NC}"

# Remove standard build/cache files
rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/ || true
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find . -type f -name '*.pyc' -delete 2>/dev/null || true

# Forcefully remove all DynaDock generated files and directories, using sudo for root-owned ones
echo -e "${YELLOW}Cleaning DynaDock generated files (may require sudo)...${NC}"
find . -type d -name ".dynadock" -exec sudo rm -rf {} + 2>/dev/null || true
find . -type d -name "caddy_data" -exec sudo rm -rf {} + 2>/dev/null || true
find . -type d -name "caddy_config" -exec sudo rm -rf {} + 2>/dev/null || true
find . -type f -name ".env.dynadock" -exec rm -f {} + 2>/dev/null || true
find . -type f -name ".dynadock_ip_map.json" -exec rm -f {} + 2>/dev/null || true
find . -type f -name "ip_map.env" -exec rm -f {} + 2>/dev/null || true

echo -e "${GREEN}✓ Clean complete${NC}"
