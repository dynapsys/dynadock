#!/usr/bin/env bash
# Clean all example Docker resources by running `dynadock down -v` where applicable.
set -euo pipefail

YELLOW="\033[0;33m"
GREEN="\033[0;32m"
NC="\033[0m"

echo -e "${YELLOW}Cleaning example resources...${NC}"

for dir in examples/*/; do
  if [ -f "${dir}/docker-compose.yaml" ]; then
    (cd "$dir" && dynadock down -v 2>/dev/null) || true
  fi
done

echo -e "${GREEN}✓ Examples cleaned${NC}"
