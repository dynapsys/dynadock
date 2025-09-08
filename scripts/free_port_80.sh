#!/usr/bin/env bash
# Free up port 80 by killing listening processes and stopping docker containers exposing it.
set -euo pipefail

YELLOW="\033[0;33m"
GREEN="\033[0;32m"
NC="\033[0m"

echo -e "${YELLOW}Freeing port 80...${NC}"

# Kill any process listening on port 80 (non-interactive)
PIDS=$(sudo lsof -t -i :80 -sTCP:LISTEN || true)
if [ -n "${PIDS}" ]; then
  echo "Killing processes listening on port 80: ${PIDS}"
  echo "${PIDS}" | xargs -r sudo kill -9 || true
fi

# Stop Docker containers publishing port 80
CONTAINERS=$(docker ps --filter "publish=80" --format "{{.ID}}" || true)
if [ -n "${CONTAINERS}" ]; then
  echo "Stopping containers publishing port 80: ${CONTAINERS}"
  echo "${CONTAINERS}" | xargs -r docker stop || true
fi

echo -e "${GREEN}✓ Port 80 is now free${NC}"
